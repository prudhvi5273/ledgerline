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
