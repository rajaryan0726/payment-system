import pytest
from app.core.exceptions import InvalidStateTransitionError
from app.models.payment import PaymentStatus
from app.repositories.payment_repo import PaymentRepository


def test_valid_state_transitions(db_session, registered_client_a):
    client, _, _ = registered_client_a

    # 1. Create payment in CREATED state
    payment = PaymentRepository.create(
        db=db_session,
        client_id=client.id,
        business_reference="order_test_101",
        idempotency_key="idemp_101",
        amount_minor=50000,
        currency="INR",
        provider="RAZORPAY",
    )
    assert payment.status == PaymentStatus.CREATED.value
    assert len(payment.events) == 1
    assert payment.events[0].event_type == "PAYMENT_CREATED"

    # 2. Transition CREATED -> PENDING
    payment = PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.PENDING.value,
        source="PROVIDER_ADAPTER",
        event_type="PROVIDER_ORDER_CREATED",
    )
    assert payment.status == PaymentStatus.PENDING.value
    assert len(payment.events) == 2

    # 3. Transition PENDING -> SUCCEEDED
    payment = PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.SUCCEEDED.value,
        source="SERVER_VERIFICATION",
        event_type="CHECKOUT_VERIFIED",
        provider_payment_id="pay_test_999",
    )
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert payment.provider_payment_id == "pay_test_999"
    assert payment.verified_at is not None
    assert len(payment.events) == 3


def test_illegal_state_transition_prevented(db_session, registered_client_a):
    client, _, _ = registered_client_a

    payment = PaymentRepository.create(
        db=db_session,
        client_id=client.id,
        business_reference="order_test_102",
        idempotency_key="idemp_102",
        amount_minor=20000,
        currency="INR",
        provider="RAZORPAY",
    )

    # CREATED -> SUCCEEDED directly without order/pending is illegal
    with pytest.raises(InvalidStateTransitionError):
        PaymentRepository.transition_status(
            db=db_session,
            payment=payment,
            new_status=PaymentStatus.SUCCEEDED.value,
            source="TEST",
            event_type="ILLEGAL_MOVE",
        )

    # Transition to SUCCEEDED properly
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
    )

    # SUCCEEDED cannot be overwritten by a late FAILED webhook
    updated = PaymentRepository.transition_status(
        db=db_session,
        payment=payment,
        new_status=PaymentStatus.FAILED.value,
        source="WEBHOOK",
        event_type="LATE_FAILED_WEBHOOK",
    )
    # Status remains SUCCEEDED safely
    assert updated.status == PaymentStatus.SUCCEEDED.value
