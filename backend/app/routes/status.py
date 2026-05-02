from fastapi import APIRouter

router = APIRouter()


@router.get("/status/{transaction_id}")
def status(transaction_id: str):
    return {
        "transaction_id": transaction_id,
        "status": "SUCCESS",
    }
