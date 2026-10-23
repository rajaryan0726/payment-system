import enum
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import (
    String,
    BigInteger,
    ForeignKey,
    DateTime,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid, utc_now


class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    ORDER_PENDING = "ORDER_PENDING"
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REFUND_PENDING = "REFUND_PENDING"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("client_application_id", "idempotency_key", name="uq_client_idempotency"),
        Index("ix_payments_client_business_ref", "client_application_id", "business_reference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    client_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("client_applications.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    business_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="RAZORPAY", nullable=False)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)  # in paise / minor units
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.CREATED.value, nullable=False, index=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client_application: Mapped["ClientApplication"] = relationship("ClientApplication", back_populates="payments")
    events: Mapped[List["PaymentEvent"]] = relationship(
        "PaymentEvent", back_populates="payment", cascade="all, delete-orphan", order_by="PaymentEvent.created_at"
    )
    refunds: Mapped[List["Refund"]] = relationship(
        "Refund", back_populates="payment", cascade="all, delete-orphan"
    )
    transfers: Mapped[List["PaymentTransfer"]] = relationship(
        "PaymentTransfer", back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # CLIENT_API, WEBHOOK, RECONCILIATION
    provider_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_payload_redacted: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="events")
