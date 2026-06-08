from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.metrics import API_ERRORS

router = APIRouter()


@router.get("/status/{transaction_id}")
def status(transaction_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT
                t.id, t.transaction_ref, t.type::text AS type, t.status::text AS status,
                t.amount, t.currency, t.description, t.legacy_latency_ms,
                t.created_at, t.processed_at, t.completed_at,
                u.full_name AS user_name, m.merchant_name
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN merchants m ON t.merchant_id = m.id
            WHERE t.id::text = :transaction_id
               OR t.transaction_ref = :transaction_id
        """),
        {"transaction_id": transaction_id}
    ).first()

    if not result:
        API_ERRORS.labels(endpoint="/status", error_code="404").inc()
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    return {
        "id": str(result.id),
        "transaction_ref": result.transaction_ref,
        "type": result.type,
        "status": result.status,
        "amount": float(result.amount),
        "currency": result.currency,
        "description": result.description,
        "legacy_latency_ms": result.legacy_latency_ms,
        "user_name": result.user_name,
        "merchant_name": result.merchant_name,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "processed_at": result.processed_at.isoformat() if result.processed_at else None,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
    }