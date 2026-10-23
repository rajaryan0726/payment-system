from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RefundCreateRequest(BaseModel):
    amount_minor: Optional[int] = Field(default=None, gt=0, description="Amount to refund in paise. If omitted, full refund.")
    idempotency_key: str = Field(..., min_length=1, max_length=128, description="Unique key to prevent duplicate refunds")
    reason: Optional[str] = Field(default=None, max_length=255, description="Reason for refund")


class RefundResponse(BaseModel):
    id: str
    payment_id: str
    provider_refund_id: Optional[str]
    amount_minor: int
    currency: str
    status: str
    reason: Optional[str]
    created_at: datetime
