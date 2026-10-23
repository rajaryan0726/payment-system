from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.webhook import WebhookEvent


class WebhookRepository:
    @staticmethod
    def get_by_event_id(db: Session, provider: str, provider_event_id: str) -> Optional[WebhookEvent]:
        return (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.provider == provider,
                WebhookEvent.provider_event_id == provider_event_id,
            )
            .first()
        )

    @staticmethod
    def record_event(
        db: Session,
        provider: str,
        provider_event_id: str,
        event_type: str,
        signature_verified: bool,
        raw_payload_redacted: Optional[Any] = None,
        processing_status: str = "PENDING",
    ) -> WebhookEvent:
        event = WebhookEvent(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            signature_verified=signature_verified,
            processing_status=processing_status,
            raw_payload_redacted=raw_payload_redacted,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def mark_processed(
        db: Session, event: WebhookEvent, status: str = "PROCESSED", error_summary: Optional[str] = None
    ) -> None:
        event.processing_status = status
        event.processed_at = datetime.now(timezone.utc)
        if error_summary:
            event.error_summary = error_summary
        db.commit()
