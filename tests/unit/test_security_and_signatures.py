import hashlib
import hmac
from app.core.logging import sanitize_message
from app.core.security import (
    generate_client_credentials,
    verify_client_secret,
    verify_hmac_sha256,
)
from app.providers.razorpay import RazorpayProvider


def test_client_credentials_hashing():
    key_id, secret, secret_hash = generate_client_credentials(is_test=True)
    assert key_id.startswith("key_test_")
    assert secret.startswith("sec_")
    assert secret_hash != secret

    assert verify_client_secret(secret, secret_hash) is True
    assert verify_client_secret("wrong_secret", secret_hash) is False


def test_checkout_signature_verification():
    provider = RazorpayProvider(
        key_id="rzp_test_sample",
        key_secret="sample_secret_key_12345",
        webhook_secret="webhook_secret_67890",
    )

    order_id = "order_sample_001"
    payment_id = "pay_sample_001"
    message = f"{order_id}|{payment_id}"
    valid_sig = hmac.new(
        b"sample_secret_key_12345", message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    assert provider.verify_checkout_signature(order_id, payment_id, valid_sig) is True
    assert provider.verify_checkout_signature(order_id, payment_id, "forged_signature_123") is False
    assert provider.verify_checkout_signature("wrong_order", payment_id, valid_sig) is False


def test_webhook_signature_verification():
    raw_payload = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123"}}}}'
    secret = "sample_webhook_secret_xyz"

    valid_sig = hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()

    assert verify_hmac_sha256(raw_payload, secret, valid_sig) is True
    assert verify_hmac_sha256(raw_payload, secret, "tampered_sig") is False
    # Signature fails if even 1 byte of raw body changes
    assert verify_hmac_sha256(raw_payload + b" ", secret, valid_sig) is False


def test_sensitive_log_sanitization():
    raw_log = 'User entered secret="super_secret_token" and card 4111 2222 3333 4444 with cvv: 123'
    sanitized = sanitize_message(raw_log)

    assert "super_secret_token" not in sanitized
    assert "4111 2222 3333 4444" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized
    assert "[REDACTED_CARD]" in sanitized
