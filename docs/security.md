# Security Architecture & Threat Model

## 1. Secrets Management
- All keys (`RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `ADMIN_API_KEY`) reside exclusively in server-side configuration.
- Client secret keys are hashed with `bcrypt` (work factor 12) before storage in `client_credentials`. Plaintext is returned strictly once upon generation.
- Secrets, authorization headers, card numbers, and CVVs are automatically redacted by `StructuredJsonFormatter` in application logs.

## 2. Cryptographic Signature Verification
1. **Frontend Checkout Callbacks**:
   Verified using HMAC-SHA256: `hex(HMAC_SHA256(order_id + "|" + payment_id, secret))`.
2. **Provider Webhooks**:
   Verified against exact raw request bytes before JSON deserialization to prevent tampering:
   `verify_hmac_sha256(raw_bytes, webhook_secret, X-Razorpay-Signature)`.

## 3. Webhook Deduplication & Replay Protection
- Every webhook event is registered in `webhook_events` with unique constraint `(provider, provider_event_id)`.
- If a delivery arrives repeatedly, the service returns `200 OK` with `duplicate: true` without applying duplicate state transitions.

## 4. Tenant Isolation
- Every payment entity contains a foreign key to `client_application_id`.
- Queries authenticate the client via API keys and restrict queries with `Payment.client_application_id == client.id`. Cross-tenant queries return `404 Not Found`.
