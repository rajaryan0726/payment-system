# System Architecture: BHIV Central Payment Service

## 1. Overview
The **BHIV Central Payment Service** is a centralized, provider-agnostic, multi-tenant payment gateway infrastructure. It decouples payment orchestration, webhook processing, signature verification, and refunds from individual client systems (such as AIAIC Farm-to-Retail and TANTRA-governed systems).

```
                      ┌─────────────────────────────────┐
                      │    BHIV Client Applications     │
                      │  (AIAIC Farm-to-Retail, etc.)   │
                      └────────────────┬────────────────┘
                                       │ Authenticated REST API
                                       │ (X-Client-Id, X-Client-Secret)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BHIV CENTRAL PAYMENT SERVICE                          │
│                                                                             │
│   ┌────────────────────┐   ┌────────────────────┐   ┌───────────────────┐   │
│   │ Client Auth Guard  │   │  Idempotency Core  │   │ State Machine &   │   │
│   │ & Tenant Isolation │   │  & Retry Engine    │   │ Append Audit Logs │   │
│   └────────────────────┘   └────────────────────┘   └───────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      Provider Abstraction Layer                     │   │
│   │                         (PaymentProvider ABC)                       │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
      ┌───────────────────────────┐         ┌───────────────────────────┐
      │   Razorpay Adapter        │         │   Future Adapters         │
      │   - Standard PG (Orders)  │         │   - Cashfree              │
      │   - Route (Marketplace)   │         │   - PayU                  │
      │   - Webhook Verifier      │         │                           │
      └─────────────┬─────────────┘         └───────────────────────────┘
                    │ HTTPS
                    ▼
          [ Razorpay API / Webhooks ]
```

## 2. Architectural Principles

1. **Provider Agnostic**: All application business logic interacts exclusively through the `PaymentProvider` interface. Razorpay details never leak to client applications.
2. **Deterministic State Machine**: Every financial event logs an append-only entry in `payment_events`. Confirmed `SUCCEEDED` transactions cannot be demoted by delayed failure webhooks.
3. **Server-Side Proof**: Frontend success screens or redirects are never authoritative. Transactions transition to `SUCCEEDED` only upon server-side cryptographic HMAC verification and authoritative provider verification.
4. **Tenant Isolation**: Multiple BHIV applications register unique client credentials. Each client can only query and refund their own transactions.
5. **Marketplace & Escrow (User A to User B)**: Supports Route split payments where User A's payment is split between the platform fee and User B's linked account, with escrow hold (`on_hold: true`) capability.
