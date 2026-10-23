import hashlib
import hmac
from typing import Any, Dict, List, Optional
import razorpay
from app.core.config import settings
from app.core.exceptions import ProviderError, SignatureVerificationError
from app.core.logging import logger
from app.core.security import verify_hmac_sha256
from app.models.payment import PaymentStatus
from app.providers.base import PaymentProvider


class RazorpayProvider(PaymentProvider):
    """Production and Test implementation of Razorpay Payment Gateway & Route."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self._key_id = key_id or settings.RAZORPAY_KEY_ID
        self._key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self._webhook_secret = webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET

        if not self._key_id or not self._key_secret:
            logger.warning("Razorpay credentials missing. Provider initialized in unconfigured state.")
            self._client = None
        else:
            self._client = razorpay.Client(auth=(self._key_id, self._key_secret))

    @property
    def provider_name(self) -> str:
        return "RAZORPAY"

    @property
    def public_key_id(self) -> str:
        return self._key_id

    async def create_order(
        self,
        internal_payment_id: str,
        amount_minor: int,
        currency: str,
        description: Optional[str] = None,
        transfers: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            raise ProviderError("Razorpay client is not configured with valid credentials.")

        payload: Dict[str, Any] = {
            "amount": amount_minor,
            "currency": currency.upper(),
            "receipt": internal_payment_id[:40],
            "notes": {
                "internal_payment_id": internal_payment_id,
                "description": description or "",
            },
        }

        # User A to User B Route split transfers
        if transfers:
            formatted_transfers = []
            for t in transfers:
                formatted_transfers.append({
                    "account": t["recipient_account_id"],
                    "amount": t["amount_minor"],
                    "currency": t.get("currency", currency).upper(),
                    "on_hold": 1 if t.get("on_hold", False) else 0,
                })
            payload["transfers"] = formatted_transfers

        try:
            order = self._client.order.create(data=payload)
            return {
                "provider_order_id": order["id"],
                "provider_status": order.get("status", "created"),
                "raw_order": order,
            }
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}", exc_info=True)
            raise ProviderError(f"Razorpay order creation failed: {str(e)}")

    def verify_checkout_signature(
        self, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        if not self._key_secret or not signature:
            return False

        message = f"{provider_order_id}|{provider_payment_id}"
        expected = hmac.new(
            self._key_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected.lower(), signature.lower())

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        if not self._webhook_secret or not signature_header:
            return False
        return verify_hmac_sha256(raw_body, self._webhook_secret, signature_header)

    async def fetch_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        if not self._client:
            raise ProviderError("Razorpay client is not configured.")
        try:
            payment = self._client.payment.fetch(provider_payment_id)
            return payment
        except Exception as e:
            logger.error(f"Error fetching Razorpay payment {provider_payment_id}: {str(e)}")
            raise ProviderError(f"Failed to fetch payment details: {str(e)}")

    async def fetch_order(self, provider_order_id: str) -> Dict[str, Any]:
        if not self._client:
            raise ProviderError("Razorpay client is not configured.")
        try:
            order = self._client.order.fetch(provider_order_id)
            return order
        except Exception as e:
            logger.error(f"Error fetching Razorpay order {provider_order_id}: {str(e)}")
            raise ProviderError(f"Failed to fetch order details: {str(e)}")

    async def initiate_refund(
        self,
        provider_payment_id: str,
        amount_minor: Optional[int] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            raise ProviderError("Razorpay client is not configured.")
        data: Dict[str, Any] = {}
        if amount_minor is not None:
            data["amount"] = amount_minor
        if notes:
            data["notes"] = notes

        try:
            refund = self._client.payment.refund(provider_payment_id, data)
            return refund
        except Exception as e:
            logger.error(f"Error initiating Razorpay refund for {provider_payment_id}: {str(e)}")
            raise ProviderError(f"Refund initiation failed: {str(e)}")

    async def release_transfer_hold(self, provider_transfer_id: str) -> Dict[str, Any]:
        if not self._client:
            raise ProviderError("Razorpay client is not configured.")
        try:
            result = self._client.transfer.edit(provider_transfer_id, {"on_hold": 0})
            return result
        except Exception as e:
            logger.error(f"Error releasing transfer hold {provider_transfer_id}: {str(e)}")
            raise ProviderError(f"Failed to release transfer hold: {str(e)}")

    def normalize_status(self, provider_status: str) -> PaymentStatus:
        status_map = {
            "created": PaymentStatus.ORDER_PENDING,
            "attempted": PaymentStatus.PENDING,
            "authorized": PaymentStatus.AUTHORIZED,
            "captured": PaymentStatus.SUCCEEDED,
            "refunded": PaymentStatus.REFUNDED,
            "failed": PaymentStatus.FAILED,
        }
        return status_map.get(provider_status.lower(), PaymentStatus.REQUIRES_RECONCILIATION)
