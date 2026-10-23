import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import (
    IdempotencyConflictError,
    RefundValidationError,
    ResourceNotFoundError,
    ProviderError,
)
from app.core.logging import logger
from app.models.client import ClientApplication
from app.models.payment import PaymentStatus
from app.models.refund import Refund
from app.providers.base import PaymentProvider
from app.providers.factory import get_payment_provider
from app.repositories.payment_repo import PaymentRepository
from app.repositories.refund_repo import RefundRepository
from app.schemas.refund import RefundCreateRequest, RefundResponse


class RefundService:
    def __init__(self, provider: Optional[PaymentProvider] = None):
        self.provider = provider or get_payment_provider()

    def initiate_refund(
        self,
        db: Session,
        client: ClientApplication,
        payment_id: str,
        request: RefundCreateRequest,
    ) -> RefundResponse:
        payment = PaymentRepository.get_by_id_and_client(db, payment_id, client.id)
        if not payment:
            raise ResourceNotFoundError("Payment", payment_id)

        if payment.status not in (PaymentStatus.SUCCEEDED.value, PaymentStatus.PARTIALLY_REFUNDED.value):
            raise RefundValidationError(
                f"Cannot refund payment in '{payment.status}' status. Payment must be SUCCEEDED."
            )

        if not payment.provider_payment_id:
            raise RefundValidationError("Cannot refund payment: missing provider_payment_id.")

        # Check idempotency
        existing_refund = RefundRepository.get_by_idempotency(db, payment.id, request.idempotency_key)
        if existing_refund:
            return self._to_response(existing_refund)

        # Calculate requested refund amount
        current_refunded = RefundRepository.get_total_refunded_minor(db, payment.id)
        remaining_refundable = payment.amount_minor - current_refunded

        refund_amount = request.amount_minor if request.amount_minor is not None else remaining_refundable

        if refund_amount <= 0:
            raise RefundValidationError("Refund amount must be greater than zero.")

        if refund_amount > remaining_refundable:
            raise RefundValidationError(
                f"Requested refund amount ({refund_amount}) exceeds remaining refundable amount ({remaining_refundable})."
            )

        # Call provider API
        try:
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    provider_result = pool.submit(
                        asyncio.run,
                        self.provider.initiate_refund(
                            provider_payment_id=payment.provider_payment_id,
                            amount_minor=refund_amount,
                            notes={"reason": request.reason or "", "internal_payment_id": payment.id},
                        ),
                    ).result()
            except RuntimeError:
                provider_result = asyncio.run(
                    self.provider.initiate_refund(
                        provider_payment_id=payment.provider_payment_id,
                        amount_minor=refund_amount,
                        notes={"reason": request.reason or "", "internal_payment_id": payment.id},
                    )
                )

            provider_refund_id = provider_result.get("id")
            refund_record = RefundRepository.create(
                db=db,
                payment_id=payment.id,
                amount_minor=refund_amount,
                currency=payment.currency,
                idempotency_key=request.idempotency_key,
                provider_refund_id=provider_refund_id,
                reason=request.reason,
                status="SUCCEEDED",
            )

            # Update parent payment status
            new_total_refunded = current_refunded + refund_amount
            new_status = (
                PaymentStatus.REFUNDED.value
                if new_total_refunded >= payment.amount_minor
                else PaymentStatus.PARTIALLY_REFUNDED.value
            )

            PaymentRepository.transition_status(
                db=db,
                payment=payment,
                new_status=new_status,
                source="CLIENT_API",
                event_type="REFUND_INITIATED",
                payload_redacted={"refund_id": refund_record.id, "amount_minor": refund_amount},
            )

            return self._to_response(refund_record)

        except Exception as e:
            logger.error(f"Failed to initiate refund for payment {payment.id}: {str(e)}")
            raise ProviderError(f"Refund initiation failed: {str(e)}")

    def get_refund(
        self, db: Session, client: ClientApplication, refund_id: str
    ) -> RefundResponse:
        refund = RefundRepository.get_by_id(db, refund_id)
        if not refund or refund.payment.client_application_id != client.id:
            raise ResourceNotFoundError("Refund", refund_id)
        return self._to_response(refund)

    def _to_response(self, refund: Refund) -> RefundResponse:
        return RefundResponse(
            id=refund.id,
            payment_id=refund.payment_id,
            provider_refund_id=refund.provider_refund_id,
            amount_minor=refund.amount_minor,
            currency=refund.currency,
            status=refund.status,
            reason=refund.reason,
            created_at=refund.created_at,
        )
