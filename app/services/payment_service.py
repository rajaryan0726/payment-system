from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import (
    IdempotencyConflictError,
    ProviderError,
    ResourceNotFoundError,
    SignatureVerificationError,
    InvalidStateTransitionError,
)
from app.core.logging import logger
from app.models.client import ClientApplication
from app.models.payment import Payment, PaymentStatus
from app.providers.base import PaymentProvider
from app.providers.factory import get_payment_provider
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    CheckoutInfo,
    PaymentCreateRequest,
    PaymentResponse,
    PaymentVerifyRequest,
)


class PaymentService:
    def __init__(self, provider: Optional[PaymentProvider] = None):
        self.provider = provider or get_payment_provider()

    def create_payment(
        self, db: Session, client: ClientApplication, request: PaymentCreateRequest
    ) -> PaymentResponse:
        # Check idempotency
        existing = PaymentRepository.get_by_idempotency_key(db, client.id, request.idempotency_key)
        if existing:
            # If payload matches, return existing record safely
            if (
                existing.amount_minor == request.amount_minor
                and existing.currency == request.currency.upper()
                and existing.business_reference == request.business_reference
            ):
                logger.info(
                    f"Idempotent retry for payment {existing.id} (key: {request.idempotency_key})",
                    extra={"payment_id": existing.id, "client_code": client.client_code},
                )
                return self._to_response(existing)
            else:
                raise IdempotencyConflictError(
                    f"Idempotency key '{request.idempotency_key}' was previously used with different parameters."
                )

        # Format transfers if provided (for User A -> User B Route splits)
        transfers_data = None
        if request.transfers:
            transfers_data = [t.model_dump() for t in request.transfers]

        # 1. Create durable internal payment in CREATED state
        payment = PaymentRepository.create(
            db=db,
            client_id=client.id,
            business_reference=request.business_reference,
            idempotency_key=request.idempotency_key,
            amount_minor=request.amount_minor,
            currency=request.currency,
            provider=self.provider.provider_name,
            description=request.description,
            transfers_data=transfers_data,
        )

        # 2. Create provider order
        try:
            import asyncio
            # If inside async event loop, run directly; otherwise loop
            try:
                loop = asyncio.get_running_loop()
                # If running inside a sync FastAPI thread pool:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    provider_result = pool.submit(
                        asyncio.run,
                        self.provider.create_order(
                            internal_payment_id=payment.id,
                            amount_minor=payment.amount_minor,
                            currency=payment.currency,
                            description=payment.description,
                            transfers=transfers_data,
                        ),
                    ).result()
            except RuntimeError:
                provider_result = asyncio.run(
                    self.provider.create_order(
                        internal_payment_id=payment.id,
                        amount_minor=payment.amount_minor,
                        currency=payment.currency,
                        description=payment.description,
                        transfers=transfers_data,
                    )
                )

            # Update with provider order ID and transition to ORDER_PENDING / PENDING
            payment.provider_order_id = provider_result["provider_order_id"]
            payment = PaymentRepository.transition_status(
                db=db,
                payment=payment,
                new_status=PaymentStatus.PENDING.value,
                source="PROVIDER_ADAPTER",
                event_type="PROVIDER_ORDER_CREATED",
                provider_status=provider_result.get("provider_status"),
                payload_redacted={"provider_order_id": provider_result["provider_order_id"]},
            )
            return self._to_response(payment)

        except Exception as e:
            logger.error(f"Provider order creation failed for payment {payment.id}: {str(e)}")
            PaymentRepository.transition_status(
                db=db,
                payment=payment,
                new_status=PaymentStatus.FAILED.value,
                source="SYSTEM",
                event_type="ORDER_CREATION_FAILED",
                failure_message=str(e),
            )
            raise ProviderError(f"Failed to initiate provider order: {str(e)}")

    def get_payment(
        self, db: Session, client: ClientApplication, payment_id: str
    ) -> PaymentResponse:
        payment = PaymentRepository.get_by_id_and_client(db, payment_id, client.id)
        if not payment:
            raise ResourceNotFoundError("Payment", payment_id)
        return self._to_response(payment)

    def verify_payment(
        self, db: Session, client: ClientApplication, payment_id: str, request: PaymentVerifyRequest
    ) -> PaymentResponse:
        payment = PaymentRepository.get_by_id_and_client(db, payment_id, client.id)
        if not payment:
            raise ResourceNotFoundError("Payment", payment_id)

        # Verify provider order matches
        if payment.provider_order_id != request.provider_order_id:
            raise SignatureVerificationError(
                f"Order ID mismatch: expected {payment.provider_order_id}, got {request.provider_order_id}"
            )

        # 1. Cryptographic HMAC verification
        is_valid = self.provider.verify_checkout_signature(
            provider_order_id=request.provider_order_id,
            provider_payment_id=request.provider_payment_id,
            signature=request.signature,
        )
        if not is_valid:
            logger.warning(
                f"Invalid checkout signature for payment {payment.id}",
                extra={"payment_id": payment.id, "order_id": request.provider_order_id},
            )
            raise SignatureVerificationError("Cryptographic signature verification failed")

        # 2. Verify authoritative provider state
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                provider_payment = pool.submit(
                    asyncio.run, self.provider.fetch_payment(request.provider_payment_id)
                ).result()
        except RuntimeError:
            provider_payment = asyncio.run(self.provider.fetch_payment(request.provider_payment_id))

        # Check amount and currency match
        if provider_payment.get("amount") != payment.amount_minor:
            raise SignatureVerificationError(
                f"Amount mismatch: expected {payment.amount_minor}, provider recorded {provider_payment.get('amount')}"
            )
        if provider_payment.get("currency", "").upper() != payment.currency:
            raise SignatureVerificationError(
                f"Currency mismatch: expected {payment.currency}, provider recorded {provider_payment.get('currency')}"
            )

        # Transition to SUCCEEDED
        payment = PaymentRepository.transition_status(
            db=db,
            payment=payment,
            new_status=PaymentStatus.SUCCEEDED.value,
            source="SERVER_VERIFICATION",
            event_type="CHECKOUT_VERIFIED",
            provider_payment_id=request.provider_payment_id,
            provider_status=provider_payment.get("status"),
            payload_redacted={
                "provider_order_id": request.provider_order_id,
                "provider_payment_id": request.provider_payment_id,
                "method": provider_payment.get("method"),
            },
        )
        return self._to_response(payment)

    def _to_response(self, payment: Payment) -> PaymentResponse:
        checkout = None
        if payment.provider_order_id:
            checkout = CheckoutInfo(
                internal_payment_id=payment.id,
                provider=payment.provider,
                provider_order_id=payment.provider_order_id,
                key_id=self.provider.public_key_id,
                amount_minor=payment.amount_minor,
                currency=payment.currency,
                description=payment.description,
            )

        return PaymentResponse(
            id=payment.id,
            client_application_id=payment.client_application_id,
            business_reference=payment.business_reference,
            provider=payment.provider,
            provider_order_id=payment.provider_order_id,
            provider_payment_id=payment.provider_payment_id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            status=payment.status,
            provider_status=payment.provider_status,
            description=payment.description,
            checkout=checkout,
            created_at=payment.created_at,
            verified_at=payment.verified_at,
        )
