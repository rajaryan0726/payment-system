# Razorpay Setup & Environment Management Guide

## 1. Test Mode Configuration (Active)

The service is currently pre-configured for test mode using your provided credentials:
- `RAZORPAY_KEY_ID`: `rzp_test_TrSyqGLleVbYzx`
- `RAZORPAY_KEY_SECRET`: Configured in `.env`
- `RAZORPAY_WEBHOOK_SECRET`: Configured in `.env`

### Testing Webhooks Locally
1. Start the service: `uvicorn app.main:app --port 8000 --reload`
2. Expose the port using ngrok / localtunnel: `ngrok http 8000`
3. On your Razorpay Dashboard (*Settings $\rightarrow$ Webhooks*):
   - Webhook URL: `https://<ngrok_url>/api/v1/webhooks/razorpay`
   - Secret: Your configured `RAZORPAY_WEBHOOK_SECRET`
   - Active Events:
     - `payment.authorized`
     - `payment.captured`
     - `payment.failed`
     - `order.paid`
     - `refund.processed`

---

## 2. Transitioning to Live Mode (Production Checklist)

To switch to Live Mode with actual money payments, complete the following steps:

1. **Razorpay Live Activation**:
   - Complete business KYC on the Razorpay Dashboard.
   - If User A to User B marketplace splits are needed, activate **Route** under *Settings $\rightarrow$ Products*.
2. **Environment Variables Update**:
   - In `.env` or production secrets manager:
     ```bash
     APP_ENV=production
     DEBUG=false
     DATABASE_URL=postgresql+psycopg2://user:password@pg-host:5432/bhiv_payments
     RAZORPAY_KEY_ID=rzp_live_your_actual_key
     RAZORPAY_KEY_SECRET=your_actual_live_secret
     RAZORPAY_WEBHOOK_SECRET=your_actual_live_webhook_secret
     ADMIN_API_KEY=generate_a_long_random_secret_string
     ```
3. **Safety Guard Enforcements**:
   - The application automatically validates that `RAZORPAY_KEY_ID` begins with `rzp_live_` whenever `APP_ENV=production`.
   - The application strictly refuses to start in production if SQLite is detected or default keys are present.
