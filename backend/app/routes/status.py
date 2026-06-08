from fastapi import APIRouter, Depends, HTTPException, Response  # tambahkan Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import read_cache, set_transaction_status_cache, status_cache_key
from app.core.database import get_db
from app.metrics import API_ERRORS

router = APIRouter()


def serialize_status_transaction(row):
    return {
        "id": str(row.id),
        "transaction_ref": row.transaction_ref,
        "type": row.type,
        "status": row.status,
        "amount": float(row.amount),
        "currency": row.currency,
        "description": row.description,
        "legacy_latency_ms": row.legacy_latency_ms,
        "user_name": row.user_name,
        "merchant_name": row.merchant_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@router.get("/status/{transaction_id}")
def status(transaction_id: str, response: Response, db: Session = Depends(get_db)):
    cached_status = read_cache(status_cache_key(transaction_id))
    if cached_status is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_status

    result = db.execute(
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
            OR t.transaction_ref = :transaction_id
            """
        ),
        {"transaction_id": transaction_id},
    ).first()

    if not result:
        API_ERRORS.labels(endpoint="/status", error_code="404").inc()
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    response_data = serialize_status_transaction(result)
    set_transaction_status_cache(response_data)

    response.headers["X-Cache"] = "MISS"

    return response_data