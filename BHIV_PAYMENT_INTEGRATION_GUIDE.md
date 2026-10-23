# BHIV Central Payment Service — Integration Guide for Client Teams

This document provides everything your engineering team needs to integrate payments into your application (AIAIC Farm-to-Retail, TANTRA systems, or any BHIV service) using the central payment infrastructure.

---

## 1. Service Details & API Documentation

- **Live Deployed API Base URL**: `https://bhiv-payment-service.onrender.com/api/v1`
- **Interactive Swagger Documentation**: `https://bhiv-payment-service.onrender.com/docs`
- **Health Check Endpoint**: `https://bhiv-payment-service.onrender.com/health`
- **Readiness Check Endpoint**: `https://bhiv-payment-service.onrender.com/ready`

---

## 2. Authentication & Credentials

Every request from your backend to the Payment Service must include two HTTP headers:

| Header | Description |
| :--- | :--- |
| `X-Client-Id` | Your unique Client Key ID |
| `X-Client-Secret` | Your Client Secret Token |

### Pre-Registered Client Credentials (AIAIC Farm-to-Retail)
For the **AIAIC Farm-to-Retail** team, your credentials on the live server are:

```env
BHIV_PAYMENT_BASE_URL=https://bhiv-payment-service.onrender.com/api/v1
BHIV_PAYMENT_CLIENT_ID=key_test_ae8ededf96d6f78eff50c687
BHIV_PAYMENT_CLIENT_SECRET=sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM
```

*(If you are integrating a different project, ask the payment service administrator to generate credentials for your `client_code`).*

---

## 3. End-to-End Integration Flow

Integrating payments takes **3 simple steps**:

```
[Your Frontend]                [Your Backend]               [Central Payment Service]      [Razorpay]
      │                              │                                  │                      │
      │ 1. Click "Pay"               │                                  │                      │
      ├─────────────────────────────>│ 2. POST /payments                │                      │
      │                              ├─────────────────────────────────>│ Creates order        │
      │                              │                                  ├─────────────────────>│
      │                              │                                  │<─────────────────────┤
      │                              │<── Returns checkout info ────────┤                      │
      │                              │    (provider_order_id, key_id)   │                      │
      │<── Passes checkout info ─────┤                                  │                      │
      │                                                                                        │
      │ 3. Opens Razorpay Checkout Popup ─────────────────────────────────────────────────────>│
      │ 4. User completes payment (UPI, Cards, Netbanking)                                     │
      │<── Returns (razorpay_payment_id, signature) ───────────────────────────────────────────┤
      │                                                                                        │
      │ 5. Sends payment evidence    │                                                         │
      ├─────────────────────────────>│ 6. POST /payments/{id}/verify                            │
      │                              ├─────────────────────────────────>│ Cryptographic check  │
      │                              │                                  │ & Provider status    │
      │                              │<── Returns status: "SUCCEEDED" ──┤                      │
      │                              │                                  │                      │
      │<── Payment Confirmed! ───────┤ (Now update your database)       │                      │
```

---

## 4. Code Examples

### Step 1: Create a Payment Order (Backend)

Call `POST /api/v1/payments` when your user initiates checkout.

> [!NOTE]
> Amounts are in **minor units** (paise for INR). For example, **₹500.00 = 50000**.

#### Python Example:
```python
import httpx

PAYMENT_API = "https://bhiv-payment-service.onrender.com/api/v1"
HEADERS = {
    "X-Client-Id": "key_test_ae8ededf96d6f78eff50c687",
    "X-Client-Secret": "sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM",
    "Content-Type": "application/json",
}

def create_order(order_id: str, amount_rupees: float):
    payload = {
        "business_reference": order_id,                 # Your internal order reference
        "amount_minor": int(amount_rupees * 100),       # e.g., 100000 for Rs. 1,000.00
        "currency": "INR",
        "idempotency_key": f"idemp_{order_id}",         # Safe retry key
        "description": f"Harvest purchase for order {order_id}"
    }

    response = httpx.post(f"{PAYMENT_API}/payments", json=payload, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    # Pass the checkout object to your frontend:
    return data["checkout"]
```

#### User A to User B Marketplace Split (Optional):
If User A is paying User B (e.g., buyer paying farmer with a platform fee and escrow hold):
```python
    payload["transfers"] = [
        {
            "recipient_account_id": "acc_farmer_linked_id",
            "amount_minor": 95000,    # Rs. 950 to farmer
            "currency": "INR",
            "on_hold": True           # Hold in escrow until delivery is confirmed
        }
    ]
```

#### Node.js / JavaScript Example:
```javascript
const axios = require('axios');

async function createPayment(orderId, amountRupees) {
  const response = await axios.post(
    'https://bhiv-payment-service.onrender.com/api/v1/payments',
    {
      business_reference: orderId,
      amount_minor: Math.round(amountRupees * 100),
      currency: 'INR',
      idempotency_key: `idemp_${orderId}_${Date.now()}`,
      description: `Payment for order ${orderId}`
    },
    {
      headers: {
        'X-Client-Id': 'key_test_ae8ededf96d6f78eff50c687',
        'X-Client-Secret': 'sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM'
      }
    }
  );

  return response.data.checkout;
}
```

---

### Step 2: Launch Checkout Popup (Frontend)

Load Razorpay Checkout in your HTML / React app:
```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

Open checkout using the `checkout` object returned by Step 1:
```javascript
function launchRazorpayCheckout(checkoutData) {
  const options = {
    key: checkoutData.key_id,                     // Public Razorpay key
    amount: checkoutData.amount_minor,            // Amount in paise
    currency: checkoutData.currency,
    name: "BHIV Ecosystem",
    description: checkoutData.description,
    order_id: checkoutData.provider_order_id,     // Razorpay order ID
    handler: async function (response) {
      // User successfully paid! Forward to your backend to verify:
      await verifyOnYourBackend({
        payment_id: checkoutData.internal_payment_id,
        provider_order_id: response.razorpay_order_id,
        provider_payment_id: response.razorpay_payment_id,
        signature: response.razorpay_signature
      });
    },
    prefill: {
      name: "Ramesh Farmer",
      email: "ramesh@example.com",
      contact: "9876543210"
    },
    theme: {
      color: "#16a34a"
    }
  };

  const rzp = new Razorpay(options);
  rzp.open();
}
```

---

### Step 3: Verify the Payment (Backend)

Once the user completes payment, your frontend receives the signature. **Never mark an order as paid until server-side verification succeeds!**

Forward the parameters to `POST /api/v1/payments/{payment_id}/verify`:

#### Python:
```python
def verify_payment(payment_id: str, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    payload = {
        "provider_order_id": razorpay_order_id,
        "provider_payment_id": razorpay_payment_id,
        "signature": razorpay_signature
    }

    res = httpx.post(f"{PAYMENT_API}/payments/{payment_id}/verify", json=payload, headers=HEADERS)
    res.raise_for_status()
    verified_data = res.json()

    if verified_data["status"] == "SUCCEEDED":
        # Authoritative proof of payment!
        # Now update your local database: order_state = "PAID"
        return True
    return False
```

#### Node.js:
```javascript
async function verifyPayment(paymentId, orderId, paymentIdProvider, signature) {
  const response = await axios.post(
    `https://bhiv-payment-service.onrender.com/api/v1/payments/${paymentId}/verify`,
    {
      provider_order_id: orderId,
      provider_payment_id: paymentIdProvider,
      signature: signature
    },
    {
      headers: {
        'X-Client-Id': 'key_test_ae8ededf96d6f78eff50c687',
        'X-Client-Secret': 'sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM'
      }
    }
  );

  return response.data.status === 'SUCCEEDED';
}
```

---

## 5. Check Payment Status Anytime

You can query the status of any payment at any time:
```http
GET https://bhiv-payment-service.onrender.com/api/v1/payments/{payment_id}/status
Headers:
  X-Client-Id: <your_key_id>
  X-Client-Secret: <your_client_secret>
```

### Response Example:
```json
{
  "id": "7a55570d-86be-4cef-9091-ab8ec73675d6",
  "business_reference": "live_test_order_001",
  "status": "SUCCEEDED",
  "provider_status": "captured",
  "amount_minor": 100000,
  "currency": "INR",
  "verified_at": "2026-10-23T21:05:00Z",
  "created_at": "2026-10-23T21:03:22Z"
}
```

### Possible Statuses:
- `PENDING`: Order created, user has not paid yet.
- `SUCCEEDED`: Payment verified on server. Safe to fulfill goods/services.
- `FAILED`: Payment failed on gateway.
- `PARTIALLY_REFUNDED`: Part of the amount was refunded.
- `REFUNDED`: 100% of amount was refunded.

---

## 6. Processing Refunds

To refund a payment (full or partial):
```http
POST https://bhiv-payment-service.onrender.com/api/v1/payments/{payment_id}/refunds
Headers:
  X-Client-Id: <your_key_id>
  X-Client-Secret: <your_client_secret>
```

```json
{
  "amount_minor": 50000,
  "idempotency_key": "refund_nonce_001",
  "reason": "Customer cancellation / goods damaged"
}
```
*(If `amount_minor` is omitted, the full remaining refundable balance is refunded).*

---

## 7. Direct Drop-In Python SDK

If your project is written in Python, you can simply copy [`client_sdk/bhiv_payment.py`](client_sdk/bhiv_payment.py) directly into your repository:

```python
from bhiv_payment import BhivPaymentClient

client = BhivPaymentClient(
    base_url="https://bhiv-payment-service.onrender.com/api/v1",
    client_id="key_test_ae8ededf96d6f78eff50c687",
    client_secret="sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM"
)

# Create order
payment = client.create_payment("order_123", amount_inr=1000.0, idempotency_key="idemp_123")

# Verify order
result = client.verify_payment(
    payment_id=payment["id"],
    razorpay_order_id=order_id,
    razorpay_payment_id=payment_id,
    razorpay_signature=signature
)
```

---

## 8. Quick cURL Test Command

You can test creating an order right from your command line:
```bash
curl -X POST "https://bhiv-payment-service.onrender.com/api/v1/payments" \
  -H "X-Client-Id: key_test_ae8ededf96d6f78eff50c687" \
  -H "X-Client-Secret: sec_uDiE7jt2Bn8Gpx_16S788BhP_DEy4Pd8qHuxHwU8SMM" \
  -H "Content-Type: application/json" \
  -d '{
    "business_reference": "terminal_test_001",
    "amount_minor": 50000,
    "currency": "INR",
    "idempotency_key": "terminal_nonce_123",
    "description": "Terminal cURL test"
  }'
```
