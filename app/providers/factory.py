from app.core.config import settings
from app.providers.base import PaymentProvider
from app.providers.razorpay import RazorpayProvider


def get_payment_provider() -> PaymentProvider:
    """Factory resolving the active PaymentProvider instance."""
    provider_name = settings.PAYMENT_PROVIDER.lower()
    if provider_name == "razorpay":
        return RazorpayProvider()
    else:
        raise ValueError(f"Unsupported payment provider: {provider_name}")
