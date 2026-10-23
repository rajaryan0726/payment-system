# API Specification: BHIV Central Payment Service

## Base URLs
- Local Development: `http://localhost:8000/api/v1`
- Health / Readiness: `http://localhost:8000/health`, `http://localhost:8000/ready`

## Authentication
Client requests require two security headers:
- `X-Client-Id`: Assigned key ID (e.g. `key_test_...`)
- `X-Client-Secret`: Assigned secret token (e.g. `sec_...`)

Administrative requests require:
- `X-Admin-Key`: Secret master key configured via `ADMIN_API_KEY`.

---

## 1. Create Payment Order
`POST /api/v1/payments`

### Request Body
```json
{
  "business_reference": "aiaic_order_1001",
  "amount_minor": 150000,
  "currency": "INR",
  "idempotency_key": "idemp_unique_nonce_123",
  "description": "Soybean harvest purchase - 10 quintals",
  "transfers": [
    {
      "recipient_account_id": "acc_farmer_linked_id",
      "amount_minor": 140000,
      "currency": "INR",
      "on_hold": true
    }
  ]
}
```

### Response (`201 Created`)
```json
{
  "id": "fe0bc229-f067-4925-82b6-9a8f4211a7c3",
  "client_application_id": "fe0bc229-...",
  "business_reference": "aiaic_order_1001",
  "provider": "RAZORPAY",
  "provider_order_id": "order_TrT9yZGuJG73Je",
  "provider_payment_id": null,
  "amount_minor": 150000,
  "currency": "INR",
  "status": "PENDING",
  "provider_status": "created",
  "description": "Soybean harvest purchase - 10 quintals",
  "checkout": {
    "internal_payment_id": "fe0bc229-f067-4925-82b6-9a8f4211a7c3",
    "provider": "RAZORPAY",
    "provider_order_id": "order_TrT9yZGuJG73Je",
    "key_id": "rzp_test_TrSyqGLleVbYzx",
    "amount_minor": 150000,
    "currency": "INR",
    "description": "Soybean harvest purchase - 10 quintals"
  },
  "created_at": "2026-10-24T01:13:36Z",
  "verified_at": null
}
```

---

## 2. Server-Side Payment Verification
`POST /api/v1/payments/{payment_id}/verify`

### Request Body
```json
{
  "provider_order_id": "order_TrT9yZGuJG73Je",
  "provider_payment_id": "pay_TrTB98a1BCde",
  "signature": "9a8f4211a7c3...hmac_sha256_hex"
}
```

### Response (`200 OK`)
Returns updated payment details with `status: "SUCCEEDED"` and `verified_at` timestamp.

---

## 3. Query Normalized Status
`GET /api/v1/payments/{payment_id}/status`

### Response (`200 OK`)
```json
{
  "id": "fe0bc229-f067-4925-82b6-9a8f4211a7c3",
  "business_reference": "aiaic_order_1001",
  "status": "SUCCEEDED",
  "provider_status": "captured",
  "amount_minor": 150000,
  "currency": "INR",
  "verified_at": "2026-10-24T01:15:00Z",
  "created_at": "2026-10-24T01:13:36Z"
}
```

---

## 4. Initiate Refund
`POST /api/v1/payments/{payment_id}/refunds`

### Request Body
```json
{
  "amount_minor": 50000,
  "idempotency_key": "idemp_refund_nonce_456",
  "reason": "Quality discrepancy at warehouse"
}
```

### Response (`201 Created`)
```json
{
  "id": "ref_88a1b2c3-...",
  "payment_id": "fe0bc229-...",
  "provider_refund_id": "rfnd_TrTX1234abcd",
  "amount_minor": 50000,
  "currency": "INR",
  "status": "SUCCEEDED",
  "reason": "Quality discrepancy at warehouse",
  "created_at": "2026-10-24T01:20:00Z"
}
```

---

## 5. Webhooks
`POST /api/v1/webhooks/razorpay`

Header: `X-Razorpay-Signature: <hmac_hex>`
Receives raw body events from Razorpay, cryptographically verifies authenticity, deduplicates via `event_id`, and safely updates transaction state.
