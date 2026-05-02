from fastapi import APIRouter
from app.services.legacy import call_legacy

router = APIRouter()


@router.post("/inquiry")
def inquiry():
    result = call_legacy(endpoint="inquiry")
    return {
        "source": "legacy",
        "transaction_type": "QRIS_INQUIRY",
        "data": result,
    }
