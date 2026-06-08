import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import QRISRequest
from app.services.legacy import call_legacy


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
        "legacy_latency_ms": row.legacy_latency_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def validate_user_and_merchant(db: Session, user_id, merchant_id):
    user = db.execute(
        text("""
            SELECT id 
            FROM users 
            WHERE id = :user_id 
              AND status = 'ACTIVE'
        """),
        {
            "user_id": str(user_id)
        }
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User tidak ditemukan atau tidak aktif"
        )

    merchant = db.execute(
        text("""
            SELECT id 
            FROM merchants 
            WHERE id = :merchant_id 
              AND status = 'ACTIVE'
        """),
        {
            "merchant_id": str(merchant_id)
        }
    ).first()

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Merchant tidak ditemukan atau tidak aktif"
        )


@router.post("/payment")
def payment(payload: QRISRequest, db: Session = Depends(get_db)):
    validate_user_and_merchant(db, payload.user_id, payload.merchant_id)

    transaction_ref = payload.transaction_ref or f"PAY-{uuid4().hex[:12].upper()}"

    try:
        legacy_result = call_legacy(endpoint="payment")

        legacy_status_code = legacy_result.get("status_code", 200)
        legacy_status_message = legacy_result.get("status", "OK")
        legacy_latency_ms = legacy_result.get("latency_ms", 0)

        result = db.execute(
            text("""
                INSERT INTO transactions (
                    transaction_ref,
                    user_id,
                    merchant_id,
                    type,
                    status,
                    amount,
                    currency,
                    description,
                    legacy_response_code,
                    legacy_response_message,
                    legacy_latency_ms,
                    processed_at,
                    completed_at
                )
                VALUES (
                    :transaction_ref,
                    :user_id,
                    :merchant_id,
                    'QRIS_PAYMENT',
                    'SUCCESS',
                    :amount,
                    'IDR',
                    :description,
                    :legacy_response_code,
                    :legacy_response_message,
                    :legacy_latency_ms,
                    NOW(),
                    NOW()
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
                    completed_at
            """),
            {
                "transaction_ref": transaction_ref,
                "user_id": str(payload.user_id),
                "merchant_id": str(payload.merchant_id),
                "amount": payload.amount,
                "description": payload.description,
                "legacy_response_code": str(legacy_status_code),
                "legacy_response_message": str(legacy_status_message),
                "legacy_latency_ms": legacy_latency_ms,
            }
        ).first()

        request_payload_json = json.dumps(
            payload.model_dump(mode="json"),
            default=str
        )

        response_payload_json = json.dumps(
            legacy_result,
            default=str
        )

        db.execute(
            text("""
                INSERT INTO legacy_calls (
                    transaction_id,
                    endpoint,
                    request_payload,
                    response_payload,
                    status_code,
                    latency_ms
                )
                VALUES (
                    :transaction_id,
                    :endpoint,
                    CAST(:request_payload AS JSONB),
                    CAST(:response_payload AS JSONB),
                    :status_code,
                    :latency_ms
                )
            """),
            {
                "transaction_id": str(result.id),
                "endpoint": "payment",
                "request_payload": request_payload_json,
                "response_payload": response_payload_json,
                "status_code": legacy_status_code,
                "latency_ms": legacy_latency_ms,
            }
        )

        db.execute(
            text("""
                INSERT INTO transaction_logs (
                    transaction_id,
                    event_name,
                    message,
                    metadata
                )
                VALUES (
                    :transaction_id,
                    'PAYMENT_SUCCESS',
                    'Payment QRIS berhasil diproses',
                    '{}'::jsonb
                )
            """),
            {
                "transaction_id": str(result.id)
            }
        )

        db.commit()

        return {
            "message": "Payment berhasil disimpan ke database",
            "data": serialize_transaction(result)
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="transaction_ref sudah digunakan"
        )

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Gagal membuat payment: {str(error)}"
        )