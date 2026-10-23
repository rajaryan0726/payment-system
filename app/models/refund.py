from typing import Optional
from sqlalchemy import String, BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class Refund(Base, TimestampMixin):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("payment_id", "idempotency_key", name="uq_payment_refund_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="INITIATED", nullable=False)  # INITIATED, SUCCEEDED, FAILED
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="refunds")
