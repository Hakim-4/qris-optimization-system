from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import (
    IDEMPOTENCY_CACHE_TTL_SECONDS,
    idempotency_cache_key,
    read_cache,
    set_transaction_status_cache,
)
from app.core.database import get_db
from app.core.rabbitmq import publish_payment_job
from app.core.redis_client import set_cache
from app.metrics import API_ERRORS, TRANSACTION_TOTAL, TRANSACTION_AMOUNT, LEGACY_LATENCY
from app.schemas import QRISRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def serialize_transaction(row):
    return {
        "id": str(row.id),
        "transaction_ref": row.transaction_ref,
        "type": row.type,
        "status": row.status,
        "amount": float(row.amount),
        "currency": row.currency,
        "description": row.description,
        "legacy_latency_ms": row.legacy_latency_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def serialize_status_transaction(row, user_name: str, merchant_name: str):
    return {
        "id": str(row.id),
        "transaction_ref": row.transaction_ref,
        "type": row.type,
        "status": row.status,
        "amount": float(row.amount),
        "currency": row.currency,
        "description": row.description,
        "legacy_latency_ms": row.legacy_latency_ms,
        "user_name": user_name,
        "merchant_name": merchant_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def validate_user_and_merchant(db: Session, user_id, merchant_id):
    user = db.execute(
        text(
            """
            SELECT id, full_name
            FROM users
            WHERE id = :user_id
            AND status = 'ACTIVE'
            """
        ),
        {"user_id": str(user_id)},
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan atau tidak aktif",
        )

    merchant = db.execute(
        text(
            """
            SELECT id, merchant_name
            FROM merchants
            WHERE id = :merchant_id
            AND status = 'ACTIVE'
            """
        ),
        {"merchant_id": str(merchant_id)},
    ).first()

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Merchant tidak ditemukan atau tidak aktif",
        )

    return user.full_name, merchant.merchant_name


def get_existing_payment_by_ref(db: Session, transaction_ref: str):
    return db.execute(
        text(
            """
            SELECT
                t.id, t.transaction_ref, t.type::text AS type, t.status::text AS status,
                t.amount, t.currency, t.description, t.legacy_latency_ms,
                t.created_at, t.processed_at, t.completed_at,
                u.full_name AS user_name, m.merchant_name
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN merchants m ON t.merchant_id = m.id
            WHERE t.transaction_ref = :transaction_ref
            AND t.type = 'QRIS_PAYMENT'
            """
        ),
        {"transaction_ref": transaction_ref},
    ).first()


def insert_payment_created_log(db: Session, transaction_id: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
            VALUES (:transaction_id, 'PAYMENT_CREATED', 'Payment QRIS dibuat dengan status PENDING', '{}'::jsonb)
            """
        ),
        {"transaction_id": transaction_id},
    )


def safe_insert_payment_queued_log(db: Session, transaction_id: str) -> None:
    try:
        db.execute(
            text(
                """
                INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
                VALUES (:transaction_id, 'PAYMENT_QUEUED', 'Payment QRIS dikirim ke RabbitMQ', '{}'::jsonb)
                """
            ),
            {"transaction_id": transaction_id},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to write PAYMENT_QUEUED log for %s: %s", transaction_id, exc)


def mark_publish_failed(db: Session, transaction_id: str, reason: str) -> None:
    db.execute(
        text(
            """
            UPDATE transactions
            SET status = 'FAILED',
                legacy_response_code = 'RABBITMQ_PUBLISH_FAILED',
                legacy_response_message = :reason,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id::text = :transaction_id
            """
        ),
        {"transaction_id": transaction_id, "reason": reason},
    )
    db.execute(
        text(
            """
            INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
            VALUES (
                :transaction_id,
                'PAYMENT_QUEUE_FAILED',
                'Payment QRIS gagal dikirim ke RabbitMQ',
                CAST(:metadata AS JSONB)
            )
            """
        ),
        {
            "transaction_id": transaction_id,
            "metadata": '{"reason":"RabbitMQ publish failed"}',
        },
    )
    db.commit()


def fetch_payment_status(db: Session, transaction_id: str):
    return db.execute(
        text(
            """
            SELECT
                t.id, t.transaction_ref, t.type::text AS type, t.status::text AS status,
                t.amount, t.currency, t.description, t.legacy_latency_ms,
                t.created_at, t.processed_at, t.completed_at,
                u.full_name AS user_name, m.merchant_name
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN merchants m ON t.merchant_id = m.id
            WHERE t.id::text = :transaction_id
            """
        ),
        {"transaction_id": transaction_id},
    ).first()


@router.post("/payment", status_code=http_status.HTTP_202_ACCEPTED)
def payment(payload: QRISRequest, db: Session = Depends(get_db)):
    transaction_ref = payload.transaction_ref or f"PAY-{uuid4().hex[:12].upper()}"
    idempotency_key = None

    if payload.transaction_ref:
        idempotency_key = idempotency_cache_key("payment", transaction_ref)
        cached_response = read_cache(idempotency_key)
        if cached_response is not None:
            return cached_response

        existing = get_existing_payment_by_ref(db, transaction_ref)
        if existing:
            response = {
                "message": "Payment sudah pernah dibuat",
                "queued": existing.status in {"PENDING", "PROCESSING"},
                "data": serialize_transaction(existing),
            }
            set_transaction_status_cache(
                serialize_status_transaction(existing, existing.user_name, existing.merchant_name)
            )
            set_cache(idempotency_key, response, ttl=IDEMPOTENCY_CACHE_TTL_SECONDS)
            return response

    try:
        user_name, merchant_name = validate_user_and_merchant(
            db,
            payload.user_id,
            payload.merchant_id,
        )
    except HTTPException as exc:
        API_ERRORS.labels(endpoint="/payment", error_code=str(exc.status_code)).inc()
        raise

    try:
        result = db.execute(
            text(
                """
                INSERT INTO transactions (
                    transaction_ref,
                    user_id,
                    merchant_id,
                    type,
                    status,
                    amount,
                    currency,
                    description
                )
                VALUES (
                    :transaction_ref,
                    :user_id,
                    :merchant_id,
                    'QRIS_PAYMENT',
                    'PENDING',
                    :amount,
                    'IDR',
                    :description
                )
                RETURNING
                    id,
                    transaction_ref,
                    type::text AS type,
                    status::text AS status,
                    amount,
                    currency,
                    description,
                    legacy_latency_ms,
                    created_at,
                    processed_at,
                    completed_at
                """
            ),
            {
                "transaction_ref": transaction_ref,
                "user_id": str(payload.user_id),
                "merchant_id": str(payload.merchant_id),
                "amount": payload.amount,
                "description": payload.description,
            },
        ).first()

        insert_payment_created_log(db, str(result.id))
        db.commit()

    except IntegrityError:
        db.rollback()
        API_ERRORS.labels(endpoint="/payment", error_code="400").inc()
        raise HTTPException(
            status_code=400,
            detail="transaction_ref sudah digunakan",
        )
    except Exception as error:
        db.rollback()
        API_ERRORS.labels(endpoint="/payment", error_code="500").inc()
        raise HTTPException(
            status_code=500,
            detail=f"Gagal membuat payment: {str(error)}",
        )

    response = {
        "message": "Payment diterima dan sedang diproses async",
        "queued": True,
        "data": serialize_transaction(result),
    }

    set_transaction_status_cache(
        serialize_status_transaction(result, user_name, merchant_name),
    )

    job_payload = {
        "transaction_id": str(result.id),
        "transaction_ref": transaction_ref,
        "user_id": str(payload.user_id),
        "merchant_id": str(payload.merchant_id),
        "amount": str(payload.amount),
        "currency": "IDR",
        "description": payload.description,
        "request_payload": payload.model_dump(mode="json"),
    }

    if not publish_payment_job(job_payload):
        try:
            mark_publish_failed(db, str(result.id), "RabbitMQ publish failed")
            failed_status = fetch_payment_status(db, str(result.id))
            if failed_status:
                set_transaction_status_cache(
                    serialize_status_transaction(
                        failed_status,
                        failed_status.user_name,
                        failed_status.merchant_name,
                    )
                )
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to mark payment %s as publish-failed: %s", result.id, exc)

        API_ERRORS.labels(endpoint="/payment", error_code="503").inc()
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Payment dibuat tetapi gagal dikirim ke RabbitMQ",
                "transaction_id": str(result.id),
                "transaction_ref": transaction_ref,
            },
        )

    safe_insert_payment_queued_log(db, str(result.id))

    # Track metrics
    TRANSACTION_TOTAL.labels(status="success", payment_method="qris").inc()
    TRANSACTION_AMOUNT.observe(float(payload.amount))

    if idempotency_key:
        set_cache(idempotency_key, response, ttl=IDEMPOTENCY_CACHE_TTL_SECONDS)

    return response
