from datetime import datetime
from typing import Optional
from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class PaymentTransfer(Base, TimestampMixin):
    """
    Represents a transfer to a recipient/seller (User B) linked account via Razorpay Route.
    Supports escrow hold (on_hold=True) until delivery/approval is granted.
    """
    __tablename__ = "payment_transfers"
    __table_args__ = (
        Index("ix_transfers_provider_transfer", "provider_transfer_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recipient_account_id: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., 'acc_G9x8Y7z...'
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    on_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    on_hold_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING, SETTLED, REVERSED
    provider_transfer_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="transfers")
