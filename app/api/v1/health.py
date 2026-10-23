from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.base import get_db
from app.schemas.common import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
def liveness() -> HealthResponse:
    """Indicates that the payment service process is alive and accepting traffic."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness Probe")
def readiness(db: Session = Depends(get_db)) -> ReadyResponse:
    """Verifies that database connectivity and provider configuration are active."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return ReadyResponse(
        status="ready" if db_status == "connected" else "not_ready",
        database=db_status,
        provider=settings.PAYMENT_PROVIDER,
    )
