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

- **Git Commit Reference:** Initial Architecture & Documentation Commit (Pending first commit).
