import pytest


def test_health_and_readiness(test_client):
    res_health = test_client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_ready = test_client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["database"] == "connected"


def test_payment_creation_requires_authentication(test_client):
    payload = {
        "business_reference": "aiaic_order_001",
        "amount_minor": 150000,
        "currency": "INR",
        "idempotency_key": "idemp_no_auth",
    }
    # No headers
    res = test_client.post("/api/v1/payments", json=payload)
    assert res.status_code == 401

    # Invalid secret
    res_bad = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": "key_fake", "X-Client-Secret": "sec_fake"},
    )
    assert res_bad.status_code == 401


def test_payment_creation_success_and_checkout_payload(test_client, registered_client_a):
    client, key_id, secret = registered_client_a

    payload = {
        "business_reference": "aiaic_order_999",
        "amount_minor": 100000,  # Rs. 1,000.00
        "currency": "INR",
        "idempotency_key": "idemp_aiaic_999",
        "description": "Soybean harvest purchase - 5 quintals",
    }

    res = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["business_reference"] == "aiaic_order_999"
    assert data["amount_minor"] == 100000
    assert data["currency"] == "INR"
    assert data["status"] == "PENDING"
    assert data["provider_order_id"].startswith("order_")
    assert data["checkout"]["key_id"] == "rzp_test_TrSyqGLleVbYzx"
    assert data["checkout"]["amount_minor"] == 100000


def test_payment_with_user_a_to_user_b_route_transfer(test_client, registered_client_a, monkeypatch):
    client, key_id, secret = registered_client_a

    # Mock provider create_order to return simulated transfer order when Route is not yet active on account
    from app.api.v1.payments import payment_service

    async def mock_create_order(*args, **kwargs):
        return {
            "provider_order_id": "order_mock_route_12345",
            "provider_status": "created",
            "raw_order": {"id": "order_mock_route_12345", "status": "created"},
        }

    monkeypatch.setattr(payment_service.provider, "create_order", mock_create_order)

    payload = {
        "business_reference": "aiaic_split_001",
        "amount_minor": 200000,  # Rs. 2,000.00 total
        "currency": "INR",
        "idempotency_key": "idemp_split_001",
        "transfers": [
            {
                "recipient_account_id": "acc_test_farmer_01",
                "amount_minor": 180000,  # Rs. 1,800.00 to Farmer
                "currency": "INR",
                "on_hold": True,  # Escrow hold until delivery
            }
        ],
    }

    res = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "PENDING"
    assert data["provider_order_id"] == "order_mock_route_12345"


def test_transfer_amount_exceeding_total_fails_validation(test_client, registered_client_a):
    client, key_id, secret = registered_client_a

    payload = {
        "business_reference": "aiaic_invalid_split",
        "amount_minor": 10000,
        "currency": "INR",
        "idempotency_key": "idemp_invalid_split",
        "transfers": [
            {
                "recipient_account_id": "acc_test_farmer_02",
                "amount_minor": 15000,  # Exceeds 10,000 total!
                "currency": "INR",
            }
        ],
    }

    res = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res.status_code == 422


def test_idempotency_behavior(test_client, registered_client_a):
    client, key_id, secret = registered_client_a

    payload = {
        "business_reference": "aiaic_idemp_check",
        "amount_minor": 50000,
        "currency": "INR",
        "idempotency_key": "idemp_repeat_key",
    }

    # First call
    res1 = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res1.status_code == 201
    payment_id1 = res1.json()["id"]

    # Repeated identical call returns same payment ID safely
    res2 = test_client.post(
        "/api/v1/payments",
        json=payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res2.status_code == 201
    assert res2.json()["id"] == payment_id1

    # Same key with different amount returns 409 Conflict
    conflict_payload = {**payload, "amount_minor": 80000}
    res3 = test_client.post(
        "/api/v1/payments",
        json=conflict_payload,
        headers={"X-Client-Id": key_id, "X-Client-Secret": secret},
    )
    assert res3.status_code == 409


def test_client_data_isolation(test_client, registered_client_a, registered_client_b):
    client_a, key_a, secret_a = registered_client_a
    client_b, key_b, secret_b = registered_client_b

    # Client A creates a payment
    res_a = test_client.post(
        "/api/v1/payments",
        json={
            "business_reference": "ref_client_a",
            "amount_minor": 30000,
            "currency": "INR",
            "idempotency_key": "idemp_a",
        },
        headers={"X-Client-Id": key_a, "X-Client-Secret": secret_a},
    )
    assert res_a.status_code == 201
    payment_id = res_a.json()["id"]

    # Client A can retrieve it
    get_res_a = test_client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-Client-Id": key_a, "X-Client-Secret": secret_a},
    )
    assert get_res_a.status_code == 200

    # Client B attempts to retrieve Client A's payment -> 404 Not Found!
    get_res_b = test_client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-Client-Id": key_b, "X-Client-Secret": secret_b},
    )
    assert get_res_b.status_code == 404
