# LedgerLine Security Threat Model & Defense Specifications (THREATS.md)

This document provides a threat model for LedgerLine, analyzing 15 distinct financial and technical attack vectors, how they could damage funds or data, the exact prevention mechanism implemented, the automated test verifying prevention, and any residual risk or operational limitation.

---

## Threat Matrix Overview

| # | Threat Name | Impact Severity | Prevention Mechanism | Test Verifying Prevention |
|---|---|---|---|---|
| 1 | Double-Spending | Critical | Row-level locking (`SELECT ... FOR UPDATE`) | `test_concurrency.py::test_concurrent_withdrawals_no_overdraft` |
| 2 | Concurrent Withdrawals | Critical | In-transaction balance check + DB lock | `test_concurrency.py::test_concurrent_withdrawals_no_overdraft` |
| 3 | Duplicate Transfer Requests | High | Two-Phase Idempotency with atomic key check | `test_idempotency.py::test_duplicate_request_same_key` |
| 4 | Unauthorized Account Access | Critical | Server-side user ownership validation | `test_auth.py::test_unauthorized_account_transfer` |
| 5 | Privilege Escalation | Critical | RBAC dependency guards (`require_role`) | `test_auditor_access.py::test_auditor_cannot_transfer` |
| 6 | Ledger Tampering | Critical | PostgreSQL DB trigger blocking UPDATE/DELETE | `test_ledger_immutability.py::test_direct_entry_update_forbidden` |
| 7 | SQL Injection | Critical | Parameterized queries via SQLAlchemy ORM | `test_auth.py::test_sql_injection_defense` |
| 8 | Replay Attacks | High | Expiring JWTs + unique idempotency keys | `test_idempotency.py::test_replayed_payload_conflict` |
| 9 | Race Conditions | High | Deterministic lock ordering (`ORDER BY id ASC`) | `test_concurrency.py::test_bidirectional_transfers_no_deadlock` |
| 10 | Transaction Failure Mid-Flight | Critical | ACID database transactions with rollback | `test_rollback.py::test_atomic_rollback_on_failure` |
| 11 | Deadlocks | High | Deterministic sorting of account IDs | `test_concurrency.py::test_bidirectional_transfers_no_deadlock` |
| 12 | Malicious / Invalid Amounts | High | Pydantic positive Decimal validator + DB check | `test_transfers.py::test_negative_or_zero_amount_rejected` |
| 13 | Authentication Abuse | Medium | Argon2id/Bcrypt + rate limiting | `test_auth.py::test_brute_force_password_hashing` |
| 14 | Sensitive Information Exposure | Medium | Response schema filtering + sanitized logging | `test_auth.py::test_password_hash_not_exposed` |
| 15 | Account Enumeration | Low | Uniform error messages + timing-neutral auth | `test_auth.py::test_uniform_auth_error_messages` |

---

## Detailed Threat Analyses

### 1. Double-Spending
- **Attack Scenario:** An account holder with a balance of ₹1,000 issues two concurrent withdrawal requests of ₹1,000 simultaneously over two separate network connections.
- **Damage Potential:** If both transactions read the balance before either writes, both succeed, leaving the account at ₹-1,000 and draining ₹1,000 of unbacked platform capital.
- **Prevention Mechanism:** The transfer engine issues `SELECT balance FROM accounts WHERE id = :id FOR UPDATE`. The second transaction is physically blocked by the PostgreSQL engine until the first transaction commits its debit. When unblocked, the second transaction reads the updated ₹0.00 balance and aborts.
- **Verifying Test:** `test_concurrent_withdrawals_no_overdraft` fires overlapping asynchronous HTTP requests.
- **Remaining Risk:** Connection pool starvation if client locks are held excessively long. Mitigated by strict database statement timeouts (`statement_timeout = 5000ms`).

### 2. Concurrent Withdrawals
- **Attack Scenario:** Multiple micro-withdrawals (e.g., 20 requests of ₹100 each against an account with ₹500) dispatched concurrently.
- **Damage Potential:** Race condition leading to overdraft and ledger imbalance.
- **Prevention Mechanism:** Exclusive row locks + database-level check constraint `CHECK (balance >= 0)`.
- **Verifying Test:** `test_concurrent_multi_withdrawal_race`.
- **Remaining Risk:** High contention under hot accounts; requests wait in lock queue. Mitigated by fail-fast lock timeouts (`NOWAIT` or `lock_timeout`).

### 3. Duplicate Transfer Requests
- **Attack Scenario:** A user initiates a ₹5,000 transfer. The request experiences network latency. The user clicks "Submit" three times or the client network stack automatically retries.
- **Damage Potential:** ₹15,000 is transferred instead of ₹5,000.
- **Prevention Mechanism:** The client attaches an `Idempotency-Key: <UUID>` header. The server creates an atomic `idempotency_records` row with status `PENDING`. Subsequent requests detect the key: if completed, they return the cached 201 response body; if in-flight, they return `409 Conflict`.
- **Verifying Test:** `test_duplicate_request_same_key`.
- **Remaining Risk:** Storage bloat of idempotency records over time. Mitigated by a scheduled retention policy (e.g., purge keys older than 30 days).

### 4. Unauthorized Account Access
- **Attack Scenario:** Attacker (User A) crafts an API call `POST /api/v1/transactions/transfer` with `source_account_id` set to User B's account ID.
- **Damage Potential:** Complete theft of third-party user funds.
- **Prevention Mechanism:** Server-side ownership guard: `SELECT id FROM accounts WHERE id = :src_id AND user_id = :current_user.id`. If not owned by caller and caller is not an authorized ADMIN, request is rejected with `403 Forbidden`.
- **Verifying Test:** `test_unauthorized_account_transfer`.
- **Remaining Risk:** Compromised user credentials (JWT theft). Mitigated by short-lived JWT access tokens (60 min) and secure HTTPS cookies/headers.

### 5. Privilege Escalation
- **Attack Scenario:** An Auditor tries to initiate a transfer or an Account Holder calls an administrative endpoint (`/api/v1/admin/users`).
- **Damage Potential:** Unauthorized money movement or alteration of account parameters.
- **Prevention Mechanism:** FastAPI dependency injection `require_role(["ADMIN"])` decodes the cryptographically signed JWT and checks claims on every protected route.
- **Verifying Test:** `test_auditor_cannot_transfer`.
- **Remaining Risk:** Role claim stale if user role changes mid-session. Mitigated by re-validating active user status against the database on critical actions.

### 6. Ledger Tampering
- **Attack Scenario:** An insider with compromised database access or an attacker exploiting an application bug executes `UPDATE ledger_entries SET amount = 0` or `DELETE FROM ledger_entries`.
- **Damage Potential:** Destruction of the audit trail, untraceable theft, regulatory non-compliance.
- **Prevention Mechanism:** A PostgreSQL trigger `trg_ledger_entries_immutability` executes `BEFORE UPDATE OR DELETE ON ledger_entries` and raises an exception. Furthermore, application database credentials should have only `SELECT` and `INSERT` on `ledger_entries`.
- **Verifying Test:** `test_direct_entry_update_forbidden`.
- **Remaining Risk:** Database superuser (`postgres`) can drop the trigger or table. Mitigated by production database privilege separation and managed cloud audit logging.

### 7. SQL Injection
- **Attack Scenario:** Malicious SQL fragment injected via transfer descriptions or search fields (`' OR '1'='1`).
- **Damage Potential:** Unauthorized data extraction or arbitrary SQL execution.
- **Prevention Mechanism:** 100% parameterization using SQLAlchemy 2.0 ORM expressions and typed Pydantic models. No raw string concatenation in SQL queries.
- **Verifying Test:** `test_sql_injection_defense`.
- **Remaining Risk:** Careless developers writing `text(f"... {user_input} ...")`. Mitigated by code review and CI linting (`bandit`).

### 8. Replay Attacks
- **Attack Scenario:** Network eavesdropper intercepts a signed transfer request and replays it minutes later.
- **Damage Potential:** Duplicate money movement.
- **Prevention Mechanism:** Mandatory TLS/HTTPS in transit. Every transfer requires a distinct `Idempotency-Key` and signed JWT with expiration timestamp (`exp`). Replayed requests with the same key return the original response without moving money.
- **Verifying Test:** `test_replayed_payload_conflict`.
- **Remaining Risk:** Stolen valid JWT within expiration window. Mitigated by HTTPS-only transmission and token revocation lists.

### 9. Race Conditions (Bidirectional Deadlocks)
- **Attack Scenario:** User A transfers ₹100 to User B while User B transfers ₹200 to User A at the exact same millisecond.
- **Damage Potential:** Circular wait deadlock: Tx1 holds Lock A, wants Lock B; Tx2 holds Lock B, wants Lock A. One transaction is forcibly aborted by PostgreSQL.
- **Prevention Mechanism:** Deterministic lock acquisition order:
  $$\text{Lock sequence} = [\min(\text{ID}_A, \text{ID}_B), \max(\text{ID}_A, \text{ID}_B)]$$
  Both transactions acquire locks in the identical order, eliminating circular wait conditions completely.
- **Verifying Test:** `test_bidirectional_transfers_no_deadlock`.
- **Remaining Risk:** Transfers involving more than 2 accounts must adhere strictly to global sorting.

### 10. Database Transaction Failure Mid-Flight
- **Attack Scenario:** Server crashes or network drops after debiting Account A but before crediting Account B.
- **Damage Potential:** ₹1,000 disappears from Account A without arriving at Account B. $\sum \text{Debit} \neq \sum \text{Credit}$.
- **Prevention Mechanism:** Single ACID database transaction block (`async with session.begin():`). If an unhandled exception or crash occurs before `commit()`, PostgreSQL performs an automatic rollback, leaving both accounts untouched.
- **Verifying Test:** `test_atomic_rollback_on_failure`.
- **Remaining Risk:** Uncommitted transactions holding locks until database timeout. Mitigated by explicit exception handlers and connection timeouts.

### 11. Deadlocks
- **Attack Scenario:** Competing transactions locking accounts out-of-order under high traffic volume.
- **Damage Potential:** High error rates, aborted transfers, degraded user experience.
- **Prevention Mechanism:** Sorted lock acquisition + strict `statement_timeout` configuration.
- **Verifying Test:** `test_concurrency_stress_no_deadlock`.
- **Remaining Risk:** Long-running analytics queries blocking write transactions. Mitigated by running reporting queries on read replicas or with `READ COMMITTED` non-locking reads.

### 12. Malicious or Invalid Amounts
- **Attack Scenario:** Attacker sends `{"amount": -500}` or `{"amount": 0}` or `{"amount": 1e20}`.
- **Damage Potential:** Negative amounts invert debit/credit logic (effectively stealing funds), while extreme values cause overflow.
- **Prevention Mechanism:** Pydantic schema validation:
  `amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)`
  Backed by database check constraints: `CHECK (amount > 0)`.
- **Verifying Test:** `test_negative_or_zero_amount_rejected`.
- **Remaining Risk:** Currency mismatch across accounts. Mitigated by requiring source and destination accounts to share the same ISO currency.

### 13. Authentication Abuse & Brute-Force Attacks
- **Attack Scenario:** Automated credential stuffing against `/api/v1/auth/login`.
- **Damage Potential:** Account takeover.
- **Prevention Mechanism:** Adaptive password hashing with Argon2id / Bcrypt (work factor 12+), preventing fast dictionary attacks. Audit logging of failed login attempts.
- **Verifying Test:** `test_brute_force_password_hashing`.
- **Remaining Risk:** Distributed botnet attacks. Mitigated by rate limiting (e.g. SlowAPI / Redis) and Cloudflare protection in production.

### 14. Sensitive Information Exposure
- **Attack Scenario:** Attacker triggers a 500 error or inspects API responses to discover password hashes, secret keys, or internal stack traces.
- **Damage Potential:** Compromise of secret credentials and blueprinting of internal infrastructure.
- **Prevention Mechanism:** Pydantic `UserOut` response schemas strictly exclude `password_hash`. FastAPI production exception handlers return sanitized generic JSON error messages: `{"detail": "Internal server error"}` while logging detailed stack traces to secure server logs only.
- **Verifying Test:** `test_password_hash_not_exposed`.
- **Remaining Risk:** Verbose logging in debug mode. Mitigated by enforcing `DEBUG=False` in production configuration.

### 15. Account Enumeration
- **Attack Scenario:** Attacker submits random emails or account numbers to determine which users exist on the platform.
- **Damage Potential:** Targeted spear-phishing and user profiling.
- **Prevention Mechanism:** Login returns identical `401 Unauthorized: Invalid credentials` regardless of whether the email exists or password was incorrect. Account numbers use high-entropy pseudorandom 12-digit formatting.
- **Verifying Test:** `test_uniform_auth_error_messages`.
- **Remaining Risk:** Timing discrepancy during password hash evaluation. Mitigated by performing a dummy hash comparison even when the email is not found.
