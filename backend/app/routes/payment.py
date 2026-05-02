from fastapi import APIRouter
from app.services.legacy import call_legacy

router = APIRouter()


@router.post("/payment")
def payment():
    result = call_legacy(endpoint="payment")
    return {
        "transaction_type": "QRIS_PAYMENT",
        "status": result["status"],
        "legacy_latency_ms": result["latency_ms"],
    }
