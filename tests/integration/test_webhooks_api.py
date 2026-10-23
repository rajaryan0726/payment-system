import hashlib
import hmac
import json
from app.core.config import settings
from app.models.payment import PaymentStatus
from app.repositories.payment_repo import PaymentRepository


def test_webhook_valid_signature_transitions_state(test_client, db_session, registered_client_a):
    client, _, _ = registered_client_a

    # Create internal payment
    payment = PaymentRepository.create(
        db=db_session,
        client_id=client.id,
        business_reference="order_hook_1",
        idempotency_key="idemp_hook_1",
        amount_minor=75000,
        currency="INR",
        provider="RAZORPAY",
    )
    payment.provider_order_id = "order_rzp_mock_123"
    PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.PENDING.value,
        source="TEST",
        event_type="ORDER_READY",
    )

    # Webhook body
    body_dict = {
        "event_id": "evt_capture_001",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_mock_123",
                    "order_id": "order_rzp_mock_123",
                    "amount": 75000,
                    "status": "captured",
                }
            }
        },
    }
    raw_body = json.dumps(body_dict).encode("utf-8")

    # Compute valid signature
    sig = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    res = test_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    assert res.json()["duplicate"] is False

    # Verify database state updated to SUCCEEDED
    db_session.refresh(payment)
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert payment.provider_payment_id == "pay_mock_123"


def test_webhook_duplicate_handling(test_client, db_session, registered_client_a):
    body_dict = {
        "event_id": "evt_repeat_002",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_dup_002", "order_id": "order_non_existent"}}},
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    # First delivery
    res1 = test_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert res1.status_code == 200
    assert res1.json()["duplicate"] is False

    # Second delivery with identical event_id
    res2 = test_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert res2.status_code == 200
    assert res2.json()["duplicate"] is True


def test_webhook_invalid_signature_rejected(test_client):
    raw_body = b'{"event":"payment.captured"}'
    res = test_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_body,
        headers={"X-Razorpay-Signature": "invalid_forged_sig", "Content-Type": "application/json"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_SIGNATURE"
