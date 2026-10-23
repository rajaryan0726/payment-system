# Client Integration Guide: AIAIC Farm-to-Retail

## 1. Overview
AIAIC Farm-to-Retail communicates with the Central Payment Service via authenticated REST APIs. 
AIAIC never connects directly to the Payment Service database or imports internal payment code.

## 2. AIAIC Workflow Steps

### Step 1: Client Application Credentials
AIAIC uses the credentials generated via `scripts/seed_client.py`:
- `X-Client-Id`: `key_test_09de11050348a218a7e81c68`
- `X-Client-Secret`: `sec_6ruF69gW_WaYzvbic-PGI0C0SxUyLAHAheVw_0wvQ1I`

### Step 2: Initiating a Payment (Python Example for AIAIC Backend)

```python
import httpx

PAYMENT_SERVICE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "X-Client-Id": "key_test_09de11050348a218a7e81c68",
    "X-Client-Secret": "sec_6ruF69gW_WaYzvbic-PGI0C0SxUyLAHAheVw_0wvQ1I",
    "Content-Type": "application/json",
}

def create_farmer_payment(order_id: str, amount_in_rupees: float, farmer_linked_acc: str):
    payload = {
        "business_reference": order_id,
        "amount_minor": int(amount_in_rupees * 100),  # Convert INR to paise
        "currency": "INR",
        "idempotency_key": f"idemp_{order_id}",
        "description": f"Harvest purchase for order {order_id}",
        "transfers": [
            {
                "recipient_account_id": farmer_linked_acc,
                "amount_minor": int(amount_in_rupees * 0.95 * 100),  # 95% to farmer, 5% fee
                "currency": "INR",
                "on_hold": True,  # Escrow hold until warehouse inspection
            }
        ],
    }

    response = httpx.post(f"{PAYMENT_SERVICE_URL}/payments", json=payload, headers=HEADERS)
    response.raise_for_status()
    payment_data = response.json()

    # Pass checkout info to AIAIC frontend
    return payment_data["checkout"]
```

### Step 3: Frontend Launch (Razorpay Standard Checkout)
AIAIC frontend loads `https://checkout.razorpay.com/v1/checkout.js` and initializes options:
```javascript
const options = {
  key: checkoutInfo.key_id,
  amount: checkoutInfo.amount_minor,
  currency: checkoutInfo.currency,
  name: "BHIV AIAIC Farm-to-Retail",
  order_id: checkoutInfo.provider_order_id,
  handler: function (response) {
    // Submit response to AIAIC backend -> Payment Service verification endpoint
    verifyPaymentOnBackend(
      checkoutInfo.internal_payment_id,
      response.razorpay_order_id,
      response.razorpay_payment_id,
      response.razorpay_signature
    );
  }
};
const rzp = new Razorpay(options);
rzp.open();
```

### Step 4: Server-Side Verification
AIAIC backend forwards the handler payload to:
```http
POST /api/v1/payments/{payment_id}/verify
{
  "provider_order_id": response.razorpay_order_id,
  "provider_payment_id": response.razorpay_payment_id,
  "signature": response.razorpay_signature
}
```
Only after this API returns `status: "SUCCEEDED"` does AIAIC update its local `payment_state` from `not_connected` to `paid`!
