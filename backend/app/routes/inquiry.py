from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
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
from app.core.redis_client import set_cache
from app.metrics import API_ERRORS
from app.schemas import QRISRequest

router = APIRouter()


def serialize_transaction(row):
    return {
        "id": str(row.id),
        "transaction_ref": row.transaction_ref,
        "type": row.type,
        "status": row.status,
        "amount": float(row.amount),
        "currency": row.currency,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
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
        "legacy_latency_ms": None,
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
        raise HTTPException(status_code=404, detail="User tidak ditemukan atau tidak aktif")

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
        raise HTTPException(status_code=404, detail="Merchant tidak ditemukan atau tidak aktif")

    return user.full_name, merchant.merchant_name


@router.post("/inquiry")
def inquiry(payload: QRISRequest, db: Session = Depends(get_db)):
    transaction_ref = payload.transaction_ref or f"INQ-{uuid4().hex[:12].upper()}"
    idempotency_key = None

    if payload.transaction_ref:
        idempotency_key = idempotency_cache_key("inquiry", transaction_ref)
        cached_response = read_cache(idempotency_key)
        if cached_response is not None:
            return cached_response

    try:
        user_name, merchant_name = validate_user_and_merchant(
            db,
            payload.user_id,
            payload.merchant_id,
        )
    except HTTPException as exc:
        API_ERRORS.labels(endpoint="/inquiry", error_code=str(exc.status_code)).inc()
        raise

    try:
        result = db.execute(
            text(
                """
                INSERT INTO transactions (
                    transaction_ref, user_id, merchant_id, type, status,
                    amount, currency, description, processed_at, completed_at
                )
                VALUES (
                    :transaction_ref, :user_id, :merchant_id, 'QRIS_INQUIRY', 'SUCCESS',
                    :amount, 'IDR', :description, NOW(), NOW()
                )
                RETURNING
                    id, transaction_ref, type::text AS type, status::text AS status,
                    amount, currency, description, created_at, processed_at, completed_at
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

        db.execute(
            text(
                """
                INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
                VALUES (:transaction_id, 'INQUIRY_CREATED', 'Inquiry QRIS berhasil dibuat', '{}'::jsonb)
                """
            ),
            {"transaction_id": str(result.id)},
        )

        db.commit()

        response = {
            "message": "Inquiry berhasil disimpan ke database",
            "data": serialize_transaction(result),
        }

        set_transaction_status_cache(
            serialize_status_transaction(result, user_name, merchant_name),
        )

        if idempotency_key:
            set_cache(idempotency_key, response, ttl=IDEMPOTENCY_CACHE_TTL_SECONDS)

        return response

    except IntegrityError:
        db.rollback()
        API_ERRORS.labels(endpoint="/inquiry", error_code="400").inc()
        raise HTTPException(status_code=400, detail="transaction_ref sudah digunakan")
    except Exception as error:
        db.rollback()
        API_ERRORS.labels(endpoint="/inquiry", error_code="500").inc()
        raise HTTPException(status_code=500, detail=f"Gagal membuat inquiry: {str(error)}")
