# Payment Lifecycle & State Machine

## 1. Domain Status Definitions

| Status | Description |
| :--- | :--- |
| `CREATED` | Internal payment entity created in durable store; provider order pending. |
| `ORDER_PENDING` | Provider order creation initiated. |
| `PENDING` | Order created on Razorpay; checkout ready for user interaction. |
| `AUTHORIZED` | Payment authorized by provider; auto-capture or manual capture pending. |
| `CAPTURED` | Payment successfully captured by provider. |
| `SUCCEEDED` | Authoritative server-side verification completed; actionable by client workflow. |
| `FAILED` | Payment failed on provider or expired. |
| `CANCELLED` | Order explicitly cancelled before payment. |
| `EXPIRED` | Order expired without payment attempt. |
| `REFUND_PENDING` | Refund initiated on provider; awaiting processing confirmation. |
| `PARTIALLY_REFUNDED` | Cumulative refund amount is strictly greater than 0 but less than order total. |
| `REFUNDED` | 100% of the order amount has been refunded. |
| `REQUIRES_RECONCILIATION` | Transient status discrepancy; requires manual or automated reconciliation. |

---

## 2. State Transition Matrix

```
[START]
   │
   ▼
CREATED ──────────► ORDER_PENDING ──────────► PENDING
                         │                         │
                         ▼                         ▼
                      FAILED               AUTHORIZED / CAPTURED
                                                   │
                                                   ▼
                                               SUCCEEDED
                                             ┌─────┴─────┐
                                             ▼           ▼
                                      REFUND_PENDING  REQUIRES_RECONCILIATION
                                             │
                                     ┌───────┴────────┐
                                     ▼                ▼
                            PARTIALLY_REFUNDED    REFUNDED
```

### Inviolable Invariants:
1. `SUCCEEDED` is a terminal positive status. A late arriving `payment.failed` webhook cannot downgrade a confirmed `SUCCEEDED` payment.
2. Every transition produces an append-only, immutable record in `payment_events`.
3. Total cumulative refunds can never exceed the parent payment's original `amount_minor`.
