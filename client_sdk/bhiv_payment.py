"""
BHIV Central Payment Service - Lightweight Client SDK
Drop this file directly into any BHIV application (AIAIC, etc.) to integrate payments.
"""

from typing import Any, Dict, List, Optional
import httpx


class BhivPaymentClient:
    """Client for communicating with the BHIV Central Payment Service."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "X-Client-Id": self.client_id,
            "X-Client-Secret": self.client_secret,
            "Content-Type": "application/json",
        }

    def create_payment(
        self,
        business_reference: str,
        amount_inr: float,
        idempotency_key: str,
        description: Optional[str] = None,
        recipient_linked_account: Optional[str] = None,
        recipient_amount_inr: Optional[float] = None,
        on_hold: bool = True,
    ) -> Dict[str, Any]:
        """
        Creates a payment order.
        Supports both standard payment and User A -> User B marketplace split.
        """
        amount_minor = int(amount_inr * 100)  # Convert rupees to paise

        payload: Dict[str, Any] = {
            "business_reference": business_reference,
            "amount_minor": amount_minor,
            "currency": "INR",
            "idempotency_key": idempotency_key,
            "description": description or f"Payment for {business_reference}",
        }

        # Optional User A -> User B Route split
        if recipient_linked_account and recipient_amount_inr:
            payload["transfers"] = [
                {
                    "recipient_account_id": recipient_linked_account,
                    "amount_minor": int(recipient_amount_inr * 100),
                    "currency": "INR",
                    "on_hold": on_hold,
                }
            ]

        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/payments", json=payload, headers=self.headers)
            res.raise_for_status()
            return res.json()

    def verify_payment(
        self, payment_id: str, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str
    ) -> Dict[str, Any]:
        """Submits frontend checkout callback evidence for server-side verification."""
        payload = {
            "provider_order_id": razorpay_order_id,
            "provider_payment_id": razorpay_payment_id,
            "signature": razorpay_signature,
        }
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(
                f"{self.base_url}/payments/{payment_id}/verify", json=payload, headers=self.headers
            )
            res.raise_for_status()
            return res.json()

    def get_status(self, payment_id: str) -> Dict[str, Any]:
        """Retrieves verified status of a payment."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/payments/{payment_id}/status", headers=self.headers)
            res.raise_for_status()
            return res.json()
