from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class ClientApplication(Base, TimestampMixin):
    __tablename__ = "client_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    client_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, REVOKED

    # Relationships
    credentials: Mapped[List["ClientCredential"]] = relationship(
        "ClientCredential", back_populates="client_application", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="client_application"
    )


class ClientCredential(Base, TimestampMixin):
    __tablename__ = "client_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    client_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("client_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, REVOKED
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client_application: Mapped["ClientApplication"] = relationship(
        "ClientApplication", back_populates="credentials"
    )
