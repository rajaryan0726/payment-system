import uuid
from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import create_engine, DateTime, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Mapped, mapped_column
from app.core.config import settings

# Engine configuration
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    settings.sqlalchemy_database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a clean database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
