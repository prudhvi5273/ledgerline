# LedgerLine AI Development & Prompt Audit Log (PROMPTS.md)

This log records every significant AI interaction, critical technical evaluation, identifying and correcting incomplete or suboptimal AI outputs, and linking them to git commits.

---

### Entry 1: Session 1 – Project Architecture & Financial Integrity Foundations

- **Date & Time:** 2026-11-06 15:35 IST
- **Prompt Given to AI:**
  Master prompt establishing the architecture, technology stack, and requirements for the Snovasys LedgerLine Hiring Challenge 2026:
  - Double-entry, append-only ledger.
  - Concurrency control with row locking.
  - Exact-once idempotency.
  - Three user roles (Admin, Account Holder, Auditor).
  - PostgreSQL schema design and 6-day execution roadmap.

- **What the AI Initially Generated:**
  - Proposed an initial architecture with React + Vite frontend, FastAPI backend, and PostgreSQL database.
  - Drafted an entity model with users, accounts, ledger entries, and idempotency keys.
  - Outlined general concurrency safety with `SELECT ... FOR UPDATE`.

- **What Was Technically Incomplete or Suboptimal (Identified During Review):**
  1. *Unbalanced External Flows:* In initial drafts of financial tables, deposits and withdrawals are often treated as simple balance updates with single-entry records. In a true double-entry system, this violates the fundamental conservation equation ($\sum \text{Debits} = \sum \text{Credits}$) because money would appear from nowhere or vanish into thin air.
  2. *Deadlock Vulnerability under Bidirectional Transfers:* Merely using `SELECT ... FOR UPDATE` is insufficient. If User A transfers to User B while User B transfers to User A simultaneously, locking in the order provided by the request payload causes an immediate circular wait deadlock in PostgreSQL.
  3. *Numeric Precision Drift:* Using standard floating-point variables (`float`) or standard integers without currency decimal scaling risks IEEE-754 rounding issues or loss of fractional currency representations.
  4. *Environment Aliasing on Windows:* The default Windows Microsoft Store execution alias for `python.exe` intercepts calls and throws `ApplicationFailedException: The file cannot be accessed by the system`.

- **How the Issue Was Investigated & Corrected:**
  1. *System Clearing Account:* Enforced a designated internal clearing account (`account_type = 'SYSTEM_CLEARING'`, e.g., `WORLD_CLEARING`). Deposits credit the user account and debit the clearing account; withdrawals debit the user account and credit the clearing account. As a result, 100% of transactions in `ledger_entries` are balanced pairs.
  2. *Deterministic Lock Ordering:* Implemented a strict rule: all row locks must be acquired in ascending UUID/string order: `sorted([source_id, dest_id])`. Circular wait conditions are rendered mathematically impossible.
  3. *Exact Fixed-Point Decimal:* Mandated PostgreSQL `NUMERIC(18, 4)` and Python `Decimal` across all tables, models, and calculation pipelines.
  4. *Schema Constraints & Immutability Trigger:* Added PostgreSQL triggers to reject any `UPDATE` or `DELETE` on `ledger_entries` at the database engine level, plus `CHECK (balance >= 0)`.
  5. *Environment Action Plan:* Flagged the Windows Python environment and detailed the cloud/local setup path for Session 2.

- **Changes Applied:**
  - Documented in `docs/DATABASE_SCHEMA.md` with complete DDL, constraints, and triggers.
  - Documented threat model and mitigations in `docs/THREATS.md`.
  - Configured project `.gitignore` and `.env.example`.

- **Git Commit Reference:** [`58be310`](https://github.com/prudhvi/ledgerline/commit/58be310) – `feat(arch): initial project architecture, database schema, threats model, and prompt audit log`

---

### Entry 2: Session 2 – Backend, Double-Entry Transfer Engine & Idempotency

- **Date & Time:** 2026-11-06 16:45 IST
- **Prompt Given to AI:**
  "Start the project" (Proceed with Second Session – Backend: complete authentication, database, accounts, transaction logic, and test suites).

- **What the AI Generated:**
  - Complete SQLAlchemy 2.0 asynchronous models (`User`, `Account`, `LedgerTransaction`, `LedgerEntry`, `IdempotencyRecord`, `AuditLog`).
  - Alembic migration `0001_initial_schema.py` including check constraints and the PostgreSQL immutability trigger preventing `UPDATE`/`DELETE` on `ledger_entries`.
  - Two-Phase Idempotency service with deterministic SHA-256 request payload hashing and concurrent in-flight conflict detection (HTTP 409).
  - Double-Entry `TransferEngine` enforcing deterministic ascending row lock ordering (`SELECT ... FOR UPDATE ORDER BY id ASC`) to eradicate deadlocks.
  - Role-based FastAPI routers for Authentication (JWT/Bcrypt), Accounts, Money Movement (Deposit, Withdraw, Transfer), Statements, Admin, and Auditor.
  - Pytest automated test suite covering Money Conservation, Insufficient Balance Rejection, Idempotency Caching, Conflict Handling, Unauthorized Access Rejection, Auditor Read-Only Enforcement, and Statement Running Balance Accuracy.

- **What Was Technically Incomplete or Suboptimal (Identified During Review):**
  1. *Audit Rollback Problem:* When a financial transaction is aborted (e.g., due to insufficient funds), calling `session.rollback()` inside standard exception handlers also cancels any audit log entries queued in that session. Refused transaction attempts would vanish from the audit trail.
  2. *Self-Transfer Edge Case:* A user submitting a transfer where `source_account_id == destination_account_id` would attempt to lock the same row twice or create zero-sum redundant lines.
  3. *Audit Log Router Separation:* Auditing endpoints needed distinct RBAC filters for Administrator versus Auditor roles rather than a single generic router.

- **How the Issue Was Investigated & Corrected:**
  1. *Isolated Audit Sessions:* Created `AuditService.log_refusal_isolated()` which spins up a standalone database session to persist security events and refusal reasons (e.g. `INSUFFICIENT_FUNDS`, `UNAUTHORIZED_ACCOUNT_ACCESS`) completely decoupled from the aborted financial session.
  2. *Pydantic Pre-Validation:* Added a `model_validator` in `TransferRequest` rejecting identical source and destination accounts before reaching the database lock manager.
  3. *Role-Segregated Audit Endpoints:* Built `/api/v1/admin/audit-logs` guarded by `require_role(["ADMIN"])` and `/api/v1/auditor/audit-logs` guarded by `require_role(["AUDITOR", "ADMIN"])`.

- **Changes Applied:**
  - Implemented in `backend/app/` across `core/`, `models/`, `schemas/`, `services/`, and `api/v1/`.
  - Added tests in `backend/tests/` and container configuration in `backend/Dockerfile` and `docker-compose.yml`.

- **Git Commit Reference:** [`434aa04`](https://github.com/prudhvi/ledgerline/commit/434aa04) – `feat(backend): complete double-entry transfer engine, auth RBAC, idempotency, and tests`

---

### Entry 3: Session 3 – Security Audit, Vulnerability Exploitation & Remediation

- **Date & Time:** 2026-11-06 17:42 IST
- **Prompt Given to AI:**
  "Act as an independent financial systems security auditor. Review my entire backend implementation. Try to identify: 1. Double-spending vulnerabilities. 2. Concurrent withdrawal race conditions. 3. Idempotency failures. 4. Authorization bypasses. 5. Ledger modification vulnerabilities. 6. Transaction rollback failures. Do not just tell me the code looks good. Write and execute actual tests to reproduce vulnerabilities. Fix the issues and explain every change. Update THREATS.md and PROMPTS.md with genuine findings. Check whether these are completed or not."

- **What the Independent Security Audit Identified (6 Genuine Vulnerabilities):**
  1. *Privilege Escalation on Public Registration:* `POST /api/v1/auth/register` accepted a client-supplied `role` field, allowing any visitor to assign themselves `ADMIN` or `AUDITOR` permissions.
  2. *Split-Commit Idempotency Anomaly:* In `transactions.py`, the financial transfer was committed first (`await db.commit()`), and the idempotency record update was committed second. A server crash or exception between the two would leave money moved while the idempotency key remained permanently stuck in `PENDING`, resulting in client lockout upon retry.
  3. *Lost Idempotency State on Aborted Transactions:* In-flight `PENDING` idempotency records flushed in the main session were obliterated when `await db.rollback()` was called on error, preventing failed attempts from being recorded.
  4. *Unhandled DB 500 on Concurrent Idempotency Race:* If two requests with the same idempotency key hit the database simultaneously, both initially found no existing record; the second raised an unhandled `IntegrityError` on the primary key, returning an unexpected 500 error instead of a clean 409 Conflict.
  5. *Clearing Account Lock Inversion:* `get_or_create_system_clearing_account` acquired a row lock (`with_for_update()`) *before* the caller executed deterministic sorted lock ordering, creating a potential deadlock window with concurrent transfers.
  6. *Ledger Immutability Gaps & Non-Finite Amounts:* While `ledger_entries` had a database trigger, `ledger_transactions` did not. Furthermore, non-finite amounts (`Infinity`, `NaN`) and sub-cent precision (> 4 decimal places) could bypass naive Pydantic filters.

- **Remediations Implemented & Verified:**
  1. *Strict Role Assignment:* Public self-registration now forcefully assigns `ACCOUNT_HOLDER`. Added protected `POST /api/v1/admin/users` for administrative provisioning of privileged roles.
  2. *Single-Commit Atomicity:* Merged financial ledger entry persistence and idempotency status update into a **single atomic transaction commit**.
  3. *Isolated Failure Logging:* Created `IdempotencyService.record_failure_isolated()` and `AuditService.log_refusal_isolated()` using independent database sessions so failure state persists across rollbacks.
  4. *Graceful Concurrent Key Interception:* Added `IntegrityError` handling in `IdempotencyService.check_or_reserve()` that catches concurrent key insertion and returns HTTP 409 Conflict.
  5. *Lock Ordering Harmonization:* Removed premature lock acquisition from the clearing account helper; locks are now acquired strictly once in deterministic ascending order.
  6. *Dual-Layer Immutability & Financial Amount Validator:* Added SQLAlchemy ORM event listeners on `LedgerEntry` and `LedgerTransaction` alongside PostgreSQL triggers, and created `validate_financial_amount()` restricting values to finite numbers with at most 4 decimal places.
  7. *Test Suite Expansion:* Added `backend/tests/test_security_attacks.py` containing tests for concurrent withdrawals, duplicate request races, ledger immutability, failure rollback atomicity, privilege escalation prevention, and non-finite amount rejection.

- **Git Commit Reference:** [`091eeac`](https://github.com/prudhvi/ledgerline/commit/091eeac) – `fix(security): resolve privilege escalation, split-commit anomaly, concurrent idempotency race, and immutability guards`

---

### Entry 4: Day 2 / Session 4 – Full-Stack Frontend Engineering (React + Vite + TypeScript)

- **Date & Time:** 2026-11-07 15:00 IST
- **Prompt Given to AI:**
  "I think day 1 complete Aipoyindhi Anukuntuna Epudu day2 start chydam ahh" (Proceeding to Day 2 – Complete Frontend Implementation and API Integration).

- **What the AI Generated:**
  - Modern, responsive React 18 + Vite + TypeScript Single-Page Application configured with Tailwind CSS, Lucide React icons, and Recharts financial visualizations.
  - `AuthContext` and Axios client configured with JWT authorization bearer headers, automatic 401 token expiration eviction, and RFC-4122 v4 UUID `Idempotency-Key` generation.
  - Role-protected route guards (`ProtectedRoute`) enforcing access boundaries for `ADMIN`, `ACCOUNT_HOLDER`, and `AUDITOR`.
  - All 14 required fintech views:
    1. **Login:** Fast-fill demo account pills (Alice Client, System Admin, Read-Only Auditor) and authentication form.
    2. **Register:** Public onboarding strictly assigning `ACCOUNT_HOLDER` role with password policy enforcement.
    3. **Dashboard:** Portfolio net balance, inflow/outflow metrics, Recharts balance area chart, and recent ledger activity feed.
    4. **Settlement Accounts:** Interactive account cards, real-time balance queries, and account opening modal.
    5. **Transfer:** Source/destination selector, balance check, auto `Idempotency-Key` generation with copy/refresh, confirmation modal, and double-entry receipt.
    6. **Deposit:** External fund inflow credited to user account with matching debit to system clearing account.
    7. **Withdrawal:** Overdraft-protected withdrawal with live balance validation and warning dialog.
    8. **Transaction History:** Filter by transaction type, search by reference ID, and expandable double-entry line items.
    9. **Statements:** Chronological ledger history with debit, credit, and running balance tracking with print/export support.
    10. **Admin Portal:** User directory, account freeze/unfreeze controls, privileged user provisioning (`POST /admin/users`), and system audit log viewer.
    11. **Auditor Portal:** Real-time double-entry equilibrium verification ($\sum \text{Debits} == \sum \text{Credits}$, Discrepancy = ₹0.0000), read-only transaction stream, and tamper-evident audit explorer.
    12. **Profile:** User security credentials overview and cryptographic principles.
    13. **Unauthorized:** 403 Access Forbidden guard page.
    14. **NotFound:** 404 Fallback routing.

- **What Was Technically Incomplete or Suboptimal (Identified During Review):**
  1. *TypeScript ImportMeta Resolution:* Missing `vite/client` type definitions caused `tsc` build error `Property 'env' does not exist on type 'ImportMeta'`.
  2. *Large Minified Bundle Warning:* Recharts and Lucide icons exceeded 500 kB single-bundle threshold in initial build.

- **How the Issue Was Investigated & Corrected:**
  1. *Vite Client Declarations:* Added `frontend/src/vite-env.d.ts` declaring `/// <reference types="vite/client" />`.
  2. *Rollup Code Splitting:* Configured `build.rollupOptions.output.manualChunks` in `vite.config.ts` splitting `vendor`, `charts`, and `icons` into separate optimized chunks.

- **Git Commit Reference:** [`73e0219`](https://github.com/prudhvi/ledgerline/commit/73e0219) – `feat(frontend): complete React Vite TypeScript fintech UI, state management, and role-based views`
