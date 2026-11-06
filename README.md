# LedgerLine – Money Movement with a Ledger You Can Prove

> **Snovasys Fresher Hiring Challenge 2026**  
> *A production-grade, secure, verifiable internal money movement platform built with Python FastAPI, PostgreSQL, and React + Vite.*

---

## 1. Executive Summary & Core Invariants

LedgerLine is built around a non-negotiable financial engineering principle: **Money is never created, destroyed, or transferred twice.**

Every money-moving operation satisfies five foundational invariants:
1. **Double-Entry Equilibrium ($\sum \text{Debits} = \sum \text{Credits}$):**
   Every transfer, deposit, and withdrawal creates balanced debit and credit entries in `ledger_entries` committed within a single atomic PostgreSQL transaction.
2. **Append-Only Immutability:**
   Ledger entries and audit logs are write-only. Database triggers prevent any `UPDATE` or `DELETE` operations on financial entries. Corrections require compensating reversal transactions.
3. **Non-Negative Balance Protection:**
   User accounts can never drop below zero (`CHECK (balance >= 0)`). Overdraft attempts under concurrent execution are prevented using row-level locking.
4. **Deterministic Concurrency & Deadlock Freedom:**
   All account rows involved in a transfer are acquired using `SELECT ... FOR UPDATE` ordered strictly by `account_id ASC`, preventing cyclical lock contention.
5. **Exact-Once Idempotency:**
   All money-moving endpoints require an `Idempotency-Key` header with payload hashing and two-phase atomic reservation.

---

## 2. Technology Stack

- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, React Router, Axios, Lucide React, Recharts.
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Pytest, HTTPX.
- **Security:** Argon2id / Bcrypt password hashing, JWT authentication, Role-Based Access Control (RBAC).
- **Database:** PostgreSQL 16+ (ACID transactions, row-level locking, check constraints, immutable triggers).
- **Deployment:** Vercel (Frontend), Render (FastAPI Web Service & PostgreSQL).

---

## 3. User Roles & Permissions

| Capability | Account Holder | Administrator | Auditor |
|---|:---:|:---:|:---:|
| View own accounts & balance | ✅ | ✅ (All accounts) | ✅ (All accounts, read-only) |
| Deposit & withdraw funds | ✅ | ❌ | ❌ |
| Transfer funds between accounts | ✅ | ❌ | ❌ |
| View transaction statement | ✅ (Own) | ✅ (All) | ✅ (All) |
| Freeze / unfreeze accounts | ❌ | ✅ | ❌ |
| Manage users & system parameters | ❌ | ✅ | ❌ |
| Verify global ledger balance | ❌ | ❌ | ✅ |
| Access security & audit logs | ❌ | ✅ | ✅ |

---

## 4. Multi-Session Development Roadmap

- **Session 1 – Architecture & Environment (Current):**
  Inspect environment, establish Git repository, define full database schema, document threats in `THREATS.md`, record `PROMPTS.md`, and validate architectural blueprint.
- **Session 2 – Backend & Database:**
  Implement SQLAlchemy models, Alembic migrations, JWT authentication, account provisioning, double-entry transfer engine, and idempotency service.
- **Session 3 – Security & Concurrency Verification:**
  Attack the system using the mandatory 12 Pytest scenarios (concurrent withdrawals, race conditions, idempotency replays, deadlocks, rollback verification).
- **Session 4 – Frontend Implementation:**
  Build professional React + Vite fintech UI (Dashboard, Accounts, Transfers, Statements, Admin, Auditor) connected to live FastAPI endpoints.
- **Session 5 – Production Deployment:**
  Deploy FastAPI and PostgreSQL on Render, React on Vercel. Verify live HTTPS APIs and CORS connectivity.
- **Session 6 – Final Review & Submission:**
  Finalize documentation, seed accounts, demo walk-through, and challenge submission package.

---

## 5. Repository Documentation Directory

- [`docs/DATABASE_SCHEMA.md`](file:///c:/Users/prudh/OneDrive/Documents/Snovasys%20project/docs/DATABASE_SCHEMA.md) – Full DDL, constraints, indices, triggers, and accounting ER diagram.
- [`docs/THREATS.md`](file:///c:/Users/prudh/OneDrive/Documents/Snovasys%20project/docs/THREATS.md) – In-depth threat model detailing 15 attack scenarios, mitigations, and verifying tests.
- [`docs/PROMPTS.md`](file:///c:/Users/prudh/OneDrive/Documents/Snovasys%20project/docs/PROMPTS.md) – AI prompt and development audit trail.
- [`.env.example`](file:///c:/Users/prudh/OneDrive/Documents/Snovasys%20project/.env.example) – Sanitized environment configuration template.
