from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QRISRequest(BaseModel):
    user_id: UUID
    merchant_id: UUID
    amount: Decimal = Field(gt=0)
    description: Optional[str] = None
    transaction_ref: Optional[str] = None
