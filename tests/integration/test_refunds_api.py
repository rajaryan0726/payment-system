import pytest
from app.models.payment import PaymentStatus
from app.repositories.payment_repo import PaymentRepository


def test_refund_rejected_on_unsuccessful_payment(test_client, db_session, registered_client_a):
    client, key_id, secret = registered_client_a

    # Payment in PENDING status
    payment = PaymentRepository.create(
        db=db_session,
        client_id=client.id,
        business_reference="ref_unpaid",
        idempotency_key="idemp_unpaid",
        amount_minor=10000,
        currency="INR",
        provider="RAZORPAY",
    )
    payment.provider_order_id = "order_sample_pending"
    PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.PENDING.value,
        source="TEST",
        event_type="PENDING_STATE",
    )

    res = test_client.post(
        f"/api/v1/payments/{payment.id}/refunds",
        json={"idempotency_key": "idemp_ref_1"},
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res.status_code == 400
    assert "must be SUCCEEDED" in res.json()["error"]["message"]


def test_refund_amount_exceeding_total_fails(test_client, db_session, registered_client_a):
    client, key_id, secret = registered_client_a

    # Payment in SUCCEEDED status
    payment = PaymentRepository.create(
        db=db_session,
        client_id=client.id,
        business_reference="ref_succ",
        idempotency_key="idemp_succ",
        amount_minor=5000,  # Rs 50.00
        currency="INR",
        provider="RAZORPAY",
    )
    payment.provider_payment_id = "pay_fake_succ"
    PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.PENDING.value,
        source="TEST",
        event_type="MOVE_TO_PENDING",
    )
    PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.SUCCEEDED.value,
        source="TEST",
        event_type="MOVE_TO_SUCCEEDED",
        provider_payment_id="pay_fake_succ",
    )

    # Attempt to refund 10,000 on a 5,000 payment
    res = test_client.post(
        f"/api/v1/payments/{payment.id}/refunds",
        json={"amount_minor": 10000, "idempotency_key": "idemp_overdraw"},
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res.status_code == 400
    assert "exceeds remaining refundable amount" in res.json()["error"]["message"]
