from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class TransferInstruction(BaseModel):
    recipient_account_id: str = Field(..., description="Provider linked account ID for User B (e.g., acc_G9x8Y7z...)")
    amount_minor: int = Field(..., gt=0, description="Amount to transfer to recipient in minor units (paise)")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    on_hold: bool = Field(default=False, description="Hold transfer in escrow until delivery confirmation")


class PaymentCreateRequest(BaseModel):
    business_reference: str = Field(..., min_length=1, max_length=128, description="Client's internal business or order reference")
    amount_minor: int = Field(..., gt=0, description="Payment amount in smallest currency unit (e.g., 10000 = Rs 100.00)")
    currency: str = Field(default="INR", min_length=3, max_length=3, description="ISO 4217 currency code")
    idempotency_key: str = Field(..., min_length=1, max_length=128, description="Unique key to guarantee safe retries")
    description: Optional[str] = Field(default=None, max_length=255, description="Short purpose or order summary")
    transfers: Optional[List[TransferInstruction]] = Field(
        default=None, description="Optional marketplace transfers to recipient/seller accounts (User B)"
    )

    @model_validator(mode="after")
    def validate_transfers_sum(self) -> "PaymentCreateRequest":
        if self.transfers:
            total_transfers = sum(t.amount_minor for t in self.transfers)
            if total_transfers > self.amount_minor:
                raise ValueError("Total transfer amount cannot exceed order amount_minor")
        return self


class CheckoutInfo(BaseModel):
    internal_payment_id: str
    provider: str
    provider_order_id: str
    key_id: str = Field(..., description="Public checkout key ID (never secret key)")
    amount_minor: int
    currency: str
    description: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    provider_order_id: str = Field(..., description="Razorpay order ID (order_...)")
    provider_payment_id: str = Field(..., description="Razorpay payment ID (pay_...)")
    signature: str = Field(..., description="Cryptographic checkout HMAC-SHA256 signature")


class PaymentResponse(BaseModel):
    id: str
    client_application_id: str
    business_reference: str
    provider: str
    provider_order_id: Optional[str]
    provider_payment_id: Optional[str]
    amount_minor: int
    currency: str
    status: str
    provider_status: Optional[str]
    description: Optional[str]
    checkout: Optional[CheckoutInfo] = None
    created_at: datetime
    verified_at: Optional[datetime] = None


class PaymentStatusResponse(BaseModel):
    id: str
    business_reference: str
    status: str
    provider_status: Optional[str]
    amount_minor: int
    currency: str
    verified_at: Optional[datetime]
    created_at: datetime
