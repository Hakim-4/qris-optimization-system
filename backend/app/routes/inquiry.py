from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import QRISRequest
from app.metrics import CACHE_HITS, CACHE_MISSES, CACHE_HIT_RATIO, API_ERRORS

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


def validate_user_and_merchant(db: Session, user_id, merchant_id):
    user = db.execute(
        text("SELECT id FROM users WHERE id = :user_id AND status = 'ACTIVE'"),
        {"user_id": str(user_id)}
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan atau tidak aktif")

    merchant = db.execute(
        text("SELECT id FROM merchants WHERE id = :merchant_id AND status = 'ACTIVE'"),
        {"merchant_id": str(merchant_id)}
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant tidak ditemukan atau tidak aktif")


def update_cache_ratio():
    hits = CACHE_HITS._value.get()
    total = hits + CACHE_MISSES._value.get()
    if total > 0:
        CACHE_HIT_RATIO.set(hits / total)


@router.post("/inquiry")
def inquiry(payload: QRISRequest, db: Session = Depends(get_db)):
    # Simulasi cache check berdasarkan merchant_id
    # Cache HIT: merchant sudah pernah di-inquiry sebelumnya (ada di transaction_logs)
    cache_check = db.execute(
        text("""
            SELECT COUNT(*) as cnt FROM transactions
            WHERE merchant_id = :merchant_id
            AND type = 'QRIS_INQUIRY'
            AND created_at > NOW() - INTERVAL '60 seconds'
        """),
        {"merchant_id": str(payload.merchant_id)}
    ).first()

    if cache_check.cnt > 0:
        # Cache HIT — merchant sudah ada inquiry dalam 60 detik terakhir
        CACHE_HITS.inc()
    else:
        # Cache MISS — pertama kali atau sudah expired
        CACHE_MISSES.inc()

    update_cache_ratio()

    try:
        validate_user_and_merchant(db, payload.user_id, payload.merchant_id)
    except HTTPException as e:
        API_ERRORS.labels(endpoint="/inquiry", error_code=str(e.status_code)).inc()
        raise

    transaction_ref = payload.transaction_ref or f"INQ-{uuid4().hex[:12].upper()}"

    try:
        result = db.execute(
            text("""
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
                    amount, currency, description, created_at, completed_at
            """),
            {
                "transaction_ref": transaction_ref,
                "user_id": str(payload.user_id),
                "merchant_id": str(payload.merchant_id),
                "amount": payload.amount,
                "description": payload.description,
            }
        ).first()

        db.execute(
            text("""
                INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
                VALUES (:transaction_id, 'INQUIRY_CREATED', 'Inquiry QRIS berhasil dibuat', '{}'::jsonb)
            """),
            {"transaction_id": str(result.id)}
        )

        db.commit()

        return {
            "message": "Inquiry berhasil disimpan ke database",
            "data": serialize_transaction(result)
        }

    except IntegrityError:
        db.rollback()
        API_ERRORS.labels(endpoint="/inquiry", error_code="400").inc()
        raise HTTPException(status_code=400, detail="transaction_ref sudah digunakan")

    except Exception as error:
        db.rollback()
        API_ERRORS.labels(endpoint="/inquiry", error_code="500").inc()
        raise HTTPException(status_code=500, detail=f"Gagal membuat inquiry: {str(error)}")