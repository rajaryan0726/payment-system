# BHIV Central Payment Service
### Standalone, Reusable, Multi-System Payment Infrastructure

A production-oriented, standalone Payment Service that acts as the central payment infrastructure for multiple independent applications within the BHIV ecosystem (including **AIAIC Farm-to-Retail** and **TANTRA-governed** systems).

---

## 🚀 Key Features

- **Provider Abstraction**: Provider-agnostic core (`PaymentProvider` ABC) with an active **Razorpay** adapter (supporting standard PG & Route split payments).
- **Server-Side Verification**: Cryptographic HMAC-SHA256 signature verification for checkout callbacks and provider webhooks.
- **Deterministic State Machine**: Explicit legal state transitions with append-only audit event logging in `payment_events`.
- **User A to User B Splits (Razorpay Route)**: Supports marketplace split payments to recipient linked accounts with escrow holds (`on_hold: true`).
- **Idempotency & Replay Protection**: Safe request retries and deduplication on incoming webhook event IDs.
- **Multi-Tenant Client Isolation**: Secure API key authentication (`bcrypt` hashed secrets) and strict tenant scoping.
- **Sensitive Data Redaction**: Automatic sanitization of secrets, tokens, card numbers, and CVVs in structured JSON logs.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13, FastAPI
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Database**: PostgreSQL (production), SQLite (zero-dependency local development/testing)
- **ORM & Migrations**: SQLAlchemy 2.0 with Alembic
- **Payment Provider**: Razorpay (official SDK + HTTP fallback)
- **Testing**: Pytest with automated unit and integration suites
- **Deployment**: Docker & Docker Compose (`compose.yaml`)

---

## 🏁 Quickstart

### 1. Setup Environment
```bash
# Clone the repository
git clone https://github.com/rajaryan0726/payment-system.git
cd payment-system

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and verify your Razorpay test credentials:
```bash
cp .env.example .env
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Register a Client Application (e.g. AIAIC)
```bash
python scripts/seed_client.py "aiaic-farm-to-retail" "AIAIC Farm to Retail"
```

### 5. Launch the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation will be available at:
`http://localhost:8000/docs`

---

## 🧪 Running Automated Tests

Run the complete test suite (unit tests, integration tests, security audits):
```bash
pytest
```

---

## 📂 Project Structure

```
payment-system/
├── app/
│   ├── main.py                     # Application entrypoint & middleware
│   ├── api/
│   │   ├── deps.py                 # Client authentication & DB injection
│   │   └── v1/
│   │       ├── health.py           # /health and /ready probes
│   │       ├── payments.py         # Payment order creation & verification
│   │       ├── refunds.py          # Authorized full/partial refunds
│   │       ├── webhooks.py         # Dedicated raw-body webhook handler
│   │       └── admin.py            # Client registration & reconciliation runs
│   ├── core/
│   │   ├── config.py               # Pydantic BaseSettings & production guards
│   │   ├── security.py             # Credential hashing & HMAC verifiers
│   │   ├── logging.py              # Structured JSON logging with redaction
│   │   └── exceptions.py           # Normalized domain exceptions
│   ├── models/                     # SQLAlchemy models (Client, Payment, Refund, Transfer)
│   ├── schemas/                    # Pydantic request/response schemas
│   ├── services/                   # Business logic (PaymentService, WebhookService, RefundService)
│   ├── providers/                  # Provider abstraction & Razorpay adapter
│   └── repositories/               # Database access objects
├── migrations/                     # Alembic migration scripts
├── tests/                          # Pytest test suite (18 automated tests)
├── docs/                           # Documentation package
│   ├── architecture.md
│   ├── api.md
│   ├── payment-lifecycle.md
│   ├── razorpay-setup.md
│   ├── client-integration.md
│   ├── security.md
│   └── operations.md
├── scripts/
│   └── seed_client.py              # Client onboarding script
├── compose.yaml                    # Multi-container Docker deployment with PostgreSQL
├── Dockerfile                      # Container build definition
└── pyproject.toml                  # Project metadata & dependencies
```

---

## 📚 Documentation Package

- [Architecture Design](docs/architecture.md)
- [API Reference](docs/api.md)
- [Payment Lifecycle & States](docs/payment-lifecycle.md)
- [Razorpay Setup & Live Transition](docs/razorpay-setup.md)
- [AIAIC Client Integration Guide](docs/client-integration.md)
- [Security & Threat Model](docs/security.md)
- [Operations & Monitoring](docs/operations.md)
