from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.models.payment import PaymentStatus


class PaymentProvider(ABC):
    """Abstract interface defining required provider operations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider, e.g., 'RAZORPAY'."""
        pass

    @property
    @abstractmethod
    def public_key_id(self) -> str:
        """Public key for client-side checkout initiation (never secret key)."""
        pass

    @abstractmethod
    async def create_order(
        self,
        internal_payment_id: str,
        amount_minor: int,
        currency: str,
        description: Optional[str] = None,
        transfers: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Creates an order on the provider.
        Returns dict containing provider_order_id and provider response metadata.
        """
        pass

    @abstractmethod
    def verify_checkout_signature(
        self, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        """Cryptographically verifies frontend checkout callback signature."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Cryptographically verifies provider webhook payload signature."""
        pass

    @abstractmethod
    async def fetch_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        """Fetches authoritative payment record from provider API."""
        pass

    @abstractmethod
    async def fetch_order(self, provider_order_id: str) -> Dict[str, Any]:
        """Fetches order record from provider API."""
        pass

    @abstractmethod
    async def initiate_refund(
        self,
        provider_payment_id: str,
        amount_minor: Optional[int] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initiates full or partial refund on the provider."""
        pass

    @abstractmethod
    async def release_transfer_hold(self, provider_transfer_id: str) -> Dict[str, Any]:
        """Releases escrow hold on a marketplace transfer to User B."""
        pass

    @abstractmethod
    def normalize_status(self, provider_status: str) -> PaymentStatus:
        """Maps provider-specific status strings to canonical PaymentStatus."""
        pass
