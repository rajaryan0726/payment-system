from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import InvalidStateTransitionError
from app.models.payment import Payment, PaymentEvent, PaymentStatus
from app.models.transfer import PaymentTransfer

# Legal state transitions definition
LEGAL_TRANSITIONS: Dict[str, List[str]] = {
    PaymentStatus.CREATED.value: [
        PaymentStatus.ORDER_PENDING.value,
        PaymentStatus.PENDING.value,
        PaymentStatus.FAILED.value,
    ],
    PaymentStatus.ORDER_PENDING.value: [
        PaymentStatus.PENDING.value,
        PaymentStatus.AUTHORIZED.value,
        PaymentStatus.CAPTURED.value,
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.FAILED.value,
        PaymentStatus.EXPIRED.value,
    ],
    PaymentStatus.PENDING.value: [
        PaymentStatus.AUTHORIZED.value,
        PaymentStatus.CAPTURED.value,
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.FAILED.value,
        PaymentStatus.CANCELLED.value,
        PaymentStatus.EXPIRED.value,
        PaymentStatus.REQUIRES_RECONCILIATION.value,
    ],
    PaymentStatus.AUTHORIZED.value: [
        PaymentStatus.CAPTURED.value,
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.FAILED.value,
    ],
    PaymentStatus.CAPTURED.value: [
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.REFUND_PENDING.value,
        PaymentStatus.PARTIALLY_REFUNDED.value,
        PaymentStatus.REFUNDED.value,
    ],
    PaymentStatus.SUCCEEDED.value: [
        PaymentStatus.REFUND_PENDING.value,
        PaymentStatus.PARTIALLY_REFUNDED.value,
        PaymentStatus.REFUNDED.value,
        PaymentStatus.REQUIRES_RECONCILIATION.value,
    ],
    PaymentStatus.REFUND_PENDING.value: [
        PaymentStatus.PARTIALLY_REFUNDED.value,
        PaymentStatus.REFUNDED.value,
        PaymentStatus.SUCCEEDED.value,  # If refund rejected
    ],
    PaymentStatus.PARTIALLY_REFUNDED.value: [
        PaymentStatus.REFUND_PENDING.value,
        PaymentStatus.REFUNDED.value,
    ],
    PaymentStatus.REFUNDED.value: [],  # Terminal state
    PaymentStatus.FAILED.value: [
        PaymentStatus.REQUIRES_RECONCILIATION.value,
    ],
    PaymentStatus.CANCELLED.value: [],
    PaymentStatus.EXPIRED.value: [],
    PaymentStatus.REQUIRES_RECONCILIATION.value: [
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.FAILED.value,
        PaymentStatus.REFUNDED.value,
    ],
}


class PaymentRepository:
    @staticmethod
    def get_by_id(db: Session, payment_id: str) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def get_by_id_and_client(db: Session, payment_id: str, client_id: str) -> Optional[Payment]:
        return db.query(Payment).filter(
            Payment.id == payment_id,
            Payment.client_application_id == client_id,
        ).first()

    @staticmethod
    def get_by_provider_order_id(db: Session, provider_order_id: str) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.provider_order_id == provider_order_id).first()

    @staticmethod
    def get_by_idempotency_key(
        db: Session, client_id: str, idempotency_key: str
    ) -> Optional[Payment]:
        return db.query(Payment).filter(
            Payment.client_application_id == client_id,
            Payment.idempotency_key == idempotency_key,
        ).first()

    @staticmethod
    def create(
        db: Session,
        client_id: str,
        business_reference: str,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
        provider: str,
        description: Optional[str] = None,
        transfers_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Payment:
        payment = Payment(
            client_application_id=client_id,
            business_reference=business_reference,
            idempotency_key=idempotency_key,
            amount_minor=amount_minor,
            currency=currency.upper(),
            provider=provider,
            status=PaymentStatus.CREATED.value,
            description=description,
        )
        db.add(payment)
        db.flush()  # Generates payment.id

        if transfers_data:
            for t in transfers_data:
                transfer = PaymentTransfer(
                    payment_id=payment.id,
                    recipient_account_id=t["recipient_account_id"],
                    amount_minor=t["amount_minor"],
                    currency=t.get("currency", currency).upper(),
                    on_hold=t.get("on_hold", False),
                    status="PENDING",
                )
                db.add(transfer)

        # Log creation event
        event = PaymentEvent(
            payment_id=payment.id,
            event_type="PAYMENT_CREATED",
            previous_status=None,
            new_status=PaymentStatus.CREATED.value,
            source="CLIENT_API",
        )
        db.add(event)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def transition_status(
        db: Session,
        payment: Payment,
        new_status: str,
        source: str,
        event_type: str,
        provider_event_id: Optional[str] = None,
        provider_payment_id: Optional[str] = None,
        provider_status: Optional[str] = None,
        payload_redacted: Optional[Any] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
    ) -> Payment:
        current_status = payment.status

        # If already in the target status, no-op but update timestamps/IDs if new
        if current_status == new_status:
            if provider_payment_id and not payment.provider_payment_id:
                payment.provider_payment_id = provider_payment_id
                db.commit()
            return payment

        # Validate legal transition
        allowed = LEGAL_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            # Special guard: Do NOT let a failure webhook overwrite an already confirmed SUCCEEDED payment
            if current_status == PaymentStatus.SUCCEEDED.value and new_status == PaymentStatus.FAILED.value:
                return payment
            raise InvalidStateTransitionError(current_status, new_status)

        # Perform transition
        payment.status = new_status
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if provider_status:
            payment.provider_status = provider_status
        if failure_code:
            payment.failure_code = failure_code
        if failure_message:
            payment.failure_message = failure_message
        if new_status in (PaymentStatus.CAPTURED.value, PaymentStatus.SUCCEEDED.value):
            payment.verified_at = datetime.now(timezone.utc)

        # Append immutable audit event
        event = PaymentEvent(
            payment_id=payment.id,
            event_type=event_type,
            previous_status=current_status,
            new_status=new_status,
            source=source,
            provider_event_id=provider_event_id,
            event_payload_redacted=payload_redacted,
        )
        db.add(event)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def list_by_client(
        db: Session,
        client_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Payment]:
        query = db.query(Payment).filter(Payment.client_application_id == client_id)
        if status:
            query = query.filter(Payment.status == status)
        return query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()
