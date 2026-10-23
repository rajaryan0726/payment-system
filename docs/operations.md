# Operations & Monitoring Guide

## 1. Running the Service Locally
```bash
# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 2. Running Migrations
```bash
# Apply pending migrations
alembic upgrade head

# Generate a new migration
alembic revision --autogenerate -m "describe_change"
```

## 3. Running Automated Tests
```bash
# Run all tests
pytest

# Run with verbose output and coverage
pytest -v --cov=app
```

## 4. Registering a Client Application
```bash
python scripts/seed_client.py "aiaic-farm-to-retail" "AIAIC Farm to Retail"
```

## 5. Reconciliation Operations
If network timeouts or delayed webhooks leave payments in `PENDING` or `REQUIRES_RECONCILIATION`:
```http
POST /api/v1/admin/reconciliation-runs
Header: X-Admin-Key: <ADMIN_API_KEY>
```
This triggers an automated background reconciliation run that cross-examines provider order records and updates state machines without manual DB intervention.
