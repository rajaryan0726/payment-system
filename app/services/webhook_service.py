import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import SignatureVerificationError
from app.core.logging import logger
from app.models.payment import PaymentStatus
from app.providers.base import PaymentProvider
from app.providers.factory import get_payment_provider
from app.repositories.payment_repo import PaymentRepository
from app.repositories.refund_repo import RefundRepository
from app.repositories.webhook_repo import WebhookRepository
from app.schemas.webhook import WebhookAck


class WebhookService:
    def __init__(self, provider: Optional[PaymentProvider] = None):
        self.provider = provider or get_payment_provider()

    def process_razorpay_webhook(
        self, db: Session, raw_body: bytes, signature_header: Optional[str]
    ) -> WebhookAck:
        if not signature_header:
            logger.warning("Webhook received without X-Razorpay-Signature header")
            raise SignatureVerificationError("Missing X-Razorpay-Signature header")

        # 1. Cryptographic HMAC verification using raw body bytes
        is_valid = self.provider.verify_webhook_signature(raw_body, signature_header)
        if not is_valid:
            logger.warning("Webhook signature verification failed")
            raise SignatureVerificationError("Invalid webhook signature")

        try:
            payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except Exception:
            raise SignatureVerificationError("Malformed JSON webhook payload")

        event_id = payload.get("event_id") or payload.get("id") or "evt_unknown"
        event_type = payload.get("event", "unknown")

        # 2. Check for deduplication
        existing = WebhookRepository.get_by_event_id(db, self.provider.provider_name, event_id)
        if existing and existing.processing_status in ("PROCESSED", "DUPLICATE"):
            logger.info(f"Duplicate webhook event ignored: {event_id}")
            return WebhookAck(event_id=event_id, duplicate=True, message="Event already processed")

        # Record incoming event audit
        event_record = WebhookRepository.record_event(
            db=db,
            provider=self.provider.provider_name,
            provider_event_id=event_id,
            event_type=event_type,
            signature_verified=True,
            raw_payload_redacted={"event": event_type, "event_id": event_id},
        )

        try:
            # 3. Handle event types safely
            self._handle_event(db, event_type, payload, event_id)
            WebhookRepository.mark_processed(db, event_record, status="PROCESSED")
            return WebhookAck(event_id=event_id, duplicate=False)
        except Exception as e:
            logger.error(f"Error handling webhook event {event_id}: {str(e)}", exc_info=True)
            WebhookRepository.mark_processed(db, event_record, status="FAILED", error_summary=str(e))
            raise

    def _handle_event(
        self, db: Session, event_type: str, payload: Dict[str, Any], event_id: str
    ) -> None:
        entity_wrapper = payload.get("payload", {})

        if event_type in ("payment.captured", "payment.authorized"):
            payment_entity = entity_wrapper.get("payment", {}).get("entity", {})
            provider_order_id = payment_entity.get("order_id")
            provider_payment_id = payment_entity.get("id")

            if provider_order_id:
                payment = PaymentRepository.get_by_provider_order_id(db, provider_order_id)
                if payment:
                    target_status = (
                        PaymentStatus.SUCCEEDED.value
                        if event_type == "payment.captured"
                        else PaymentStatus.AUTHORIZED.value
                    )
                    PaymentRepository.transition_status(
                        db=db,
                        payment=payment,
                        new_status=target_status,
                        source="WEBHOOK",
                        event_type=f"WEBHOOK_{event_type.upper().replace('.', '_')}",
                        provider_event_id=event_id,
                        provider_payment_id=provider_payment_id,
                        provider_status=payment_entity.get("status"),
                    )

        elif event_type == "payment.failed":
            payment_entity = entity_wrapper.get("payment", {}).get("entity", {})
            provider_order_id = payment_entity.get("order_id")
            if provider_order_id:
                payment = PaymentRepository.get_by_provider_order_id(db, provider_order_id)
                if payment:
                    PaymentRepository.transition_status(
                        db=db,
                        payment=payment,
                        new_status=PaymentStatus.FAILED.value,
                        source="WEBHOOK",
                        event_type="WEBHOOK_PAYMENT_FAILED",
                        provider_event_id=event_id,
                        failure_code=payment_entity.get("error_code"),
                        failure_message=payment_entity.get("error_description"),
                    )

        elif event_type == "refund.processed":
            refund_entity = entity_wrapper.get("refund", {}).get("entity", {})
            provider_payment_id = refund_entity.get("payment_id")
            provider_refund_id = refund_entity.get("id")
            amount = refund_entity.get("amount")

            if provider_payment_id:
                payment = (
                    db.query(PaymentRepository)
                    .filter(PaymentRepository.provider_payment_id == provider_payment_id)
                    .first()
                )
                if payment:
                    total_refunded = RefundRepository.get_total_refunded_minor(db, payment.id)
                    new_status = (
                        PaymentStatus.REFUNDED.value
                        if total_refunded >= payment.amount_minor
                        else PaymentStatus.PARTIALLY_REFUNDED.value
                    )
                    PaymentRepository.transition_status(
                        db=db,
                        payment=payment,
                        new_status=new_status,
                        source="WEBHOOK",
                        event_type="WEBHOOK_REFUND_PROCESSED",
                        provider_event_id=event_id,
                    )
