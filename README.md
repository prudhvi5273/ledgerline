# LedgerLine – Money Movement with a Ledger You Can Prove

> **Snovasys Fresher Hiring Challenge 2026**  
> *A production-grade, verifiable internal money movement platform built with Python FastAPI, PostgreSQL, and React + Vite.*  
> **GitHub Repository:** [https://github.com/prudhvi5273/ledgerline](https://github.com/prudhvi5273/ledgerline)

---

## 1. Executive Summary & Core Financial Invariants

LedgerLine is engineered for mission-critical financial systems where money movement must be provable, auditable, and immutable. It adheres strictly to the rule: **Money is never created, destroyed, or transferred twice.**

Every financial operation satisfies five core mathematical invariants:
1. **Double-Entry Equilibrium ($\sum \text{Debits} = \sum \text{Credits}$):**
   Every transfer, deposit, and withdrawal creates balanced debit and credit entries in `ledger_entries` committed within a single atomic database transaction. External inflows and outflows balance against an internal settlement account (`SYSTEM_CLEARING`).
2. **Append-Only Immutability:**
   Ledger entries and transaction records are strictly write-only. PostgreSQL triggers (`trg_ledger_entries_immutability`, `trg_ledger_transactions_immutability`) and SQLAlchemy ORM event listeners block any `UPDATE` or `DELETE` queries.
3. **Strict Non-Negative Balance Protection:**
   User accounts can never drop below zero (`CHECK (account_type = 'SYSTEM_CLEARING' OR balance >= 0)`). Overdraft attempts under concurrent execution are rejected using row-level locks (`SELECT ... FOR UPDATE`).
4. **Deterministic Concurrency & Deadlock Freedom:**
   When moving funds between two accounts, row locks are acquired in strict deterministic ascending order (`ORDER BY id ASC`). Cyclical wait dependencies are rendered mathematically impossible.
5. **Exact-Once Idempotency:**
   All money-moving endpoints require an `Idempotency-Key` header. Requests are hashed with SHA-256. Duplicate requests return identical cached responses without executing secondary financial movements, while in-flight or modified payload retries return HTTP `409 Conflict`.

---

## 2. Technology Stack

### Backend Architecture
- **Language & Framework:** Python 3.11+, FastAPI (REST API with OpenAPI / Swagger documentation).
- **ORM & Migrations:** SQLAlchemy 2.0 (asynchronous engine with connection pooling), Alembic.
- **Data Validation:** Pydantic v2 (strict Decimal validators restricting non-finite numbers and bounding precision to 4 decimal places).
- **Security & RBAC:** Argon2id & Bcrypt password hashing, signed JWT (JSON Web Tokens), Role-Based Access Control guards.
- **Testing:** Pytest, pytest-asyncio, HTTPX, isolated database sessions.

### Frontend Architecture
- **Framework & Tooling:** React 18, Vite, TypeScript.
- **Styling & Icons:** Tailwind CSS (custom dark fintech palette), Lucide React.
- **Visualizations:** Recharts (portfolio trajectory and volume analysis).
- **Client & Routing:** Axios (JWT and error interceptors, RFC-4122 v4 UUID Idempotency-Key generator), React Router v7.

### Database & Deployment
- **Database:** PostgreSQL 16+ (ACID transactions, row-level locking, foreign keys, check constraints, database triggers).
- **Containers:** Docker, Docker Compose.
- **Cloud Hosting:** Render (FastAPI Web Service & PostgreSQL), Vercel (React Frontend).

---

## 3. Features Implemented

### Role-Based Access Control (RBAC)
- **Account Holder:** View own accounts and balances, transfer funds between accounts, deposit external funds, execute overdraft-protected withdrawals, download chronological statements.
- **Administrator:** Full visibility across all platform users and accounts, provision privileged users (`ADMIN`, `AUDITOR`), freeze/unfreeze accounts, and inspect system audit logs.
- **Auditor:** Dedicated read-only access to all accounts, transactions, and audit records. Features a real-time **Ledger Reconciliation Tool** verifying that total debits equal total credits with zero discrepancy. Prohibited from executing money movements.

### Frontend Application Modules (14 Screens)
1. **Login Page:** Clean authentication form with fast-fill demo credentials for Client, Admin, and Auditor roles.
2. **Registration Page:** Self-service client onboarding strictly enforcing `ACCOUNT_HOLDER` role assignment.
3. **Fintech Dashboard:** Portfolio net balance, active account counters, Recharts balance trajectory area chart, recent ledger feed, and quick transfer shortcuts.
4. **Settlement Accounts:** Interactive account cards, balance breakdown, status badges, and an "Open New Account" modal (INR, USD, EUR; Checking, Savings).
5. **Money Transfer Page:** Source and destination picker, live balance check, auto-generated unique `Idempotency-Key` with copy/refresh tools, confirmation modal, and atomic double-entry receipt.
6. **Deposit Page:** External cash inflow form credited to user account and debited to system clearing account.
7. **Withdrawal Page:** Overdraft-protected withdrawal with live balance validation and warning alert.
8. **Transaction History:** Filter by transaction type, search by reference ID, and expandable double-entry line items.
9. **Account Statements:** Chronological ledger history with debit, credit, and running balance tracking with print/export support.
10. **Admin Portal:** User directory, account freeze/unfreeze controls, privileged user provisioning (`POST /admin/users`), and system audit log viewer.
11. **Auditor Portal:** Real-time double-entry equilibrium verification ($\sum \text{Debits} == \sum \text{Credits}$, Discrepancy = ₹0.0000), read-only transaction stream, and tamper-evident audit explorer.
12. **Profile & Security Settings:** User credentials overview and cryptographic principles.
13. **Unauthorized Access Page (403):** Role-boundary guard page.
14. **Not Found Page (404):** Route fallback handler.
15. **AI Financial Assistant (Chatbot):** Interactive AI companion advising users on double-entry equilibrium, concurrency row-locking invariants, idempotency replay tokens, and real-time balance calculations.

---

## 4. Demo Seed Credentials

Use these demo credentials to test all three roles.

| Role | Email | Password | Permissions & Scope |
|:---:|:---:|:---:|---|
| **Account Holder** | `client.alice@example.com` | `SecretPassword123!` | Standard banking: create accounts, deposit, withdraw, transfer, statements. |
| **Administrator** | `admin.root@example.com` | `AdminMasterPass123!` | System admin: view all users/accounts, freeze accounts, view audit logs. |
| **Auditor** | `auditor.check@example.com` | `AuditorPass123!` | Read-only compliance: verify $\sum \text{Debits} == \sum \text{Credits}$, inspect audit logs. |

---

## 5. Local Setup & Installation

### Prerequisites
- Node.js `v20+` & npm `v10+`
- Python `3.11+`
- PostgreSQL `16+` (or Docker)

### Option A: Running with Docker Compose (1-Command Full Stack)
```bash
# Clone the repository
git clone https://github.com/prudhvi5273/ledgerline.git
cd ledgerline

# Start all 3 tiers: PostgreSQL 16, FastAPI Backend, and React Frontend
docker-compose up --build -d
```
- **React Frontend**: `http://localhost:3000` (or `http://localhost:5173` via Vite dev)
- **FastAPI OpenAPI Swagger**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Initial Data**: Demo accounts (`Alice`, `Bob`, `Admin`, `Auditor`) are auto-seeded on launch with double-entry balance history!

### Option B: Manual Local Setup

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: `http://localhost:8000/docs`

#### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend will be live at: `http://localhost:5173`

---

## 6. Automated Testing Suite

The test suite validates all 12 mandatory challenge criteria:

```bash
cd backend
pytest -v
```

### Mandatory Test Coverage Breakdown

| Test # | Test Scenario | Test Implementation File | Verification Goal |
|:---:|---|---|---|
| **1** | Money Conservation | `tests/test_money_conservation.py` | Sender loses ₹1,000, receiver gains ₹1,000; total system balance unchanged; $\sum \text{Debits} = \sum \text{Credits}$. |
| **2** | Insufficient Balance | `tests/test_insufficient_balance.py` | Attempt to withdraw ₹600 from ₹500 balance rejected; balance unchanged. |
| **3** | Idempotency Replay | `tests/test_idempotency.py` | Duplicate request returns cached response; exactly 1 financial transaction created. |
| **4** | Payload Mismatch Conflict | `tests/test_idempotency.py` | Reusing key with altered amount returns HTTP 409 Conflict. |
| **5** | Concurrent Withdrawals | `tests/test_security_attacks.py` | Two simultaneous ₹800 withdrawals against ₹1,000 balance: exactly 1 succeeds, balance reaches ₹200 (never negative). |
| **6** | Concurrent Duplicate Requests | `tests/test_security_attacks.py` | Simultaneous requests with identical key execute exactly once without 500 error. |
| **7** | Unauthorized Transfer | `tests/test_auth_and_roles.py` | User A transferring from User B's account is rejected with 403 Forbidden. |
| **8** | Auditor Read-Only Access | `tests/test_auth_and_roles.py` | Auditor attempting deposit, withdrawal, or transfer is rejected with 403 Forbidden. |
| **9** | Ledger Immutability | `tests/test_security_attacks.py` | SQL `UPDATE` and `DELETE` on posted entries blocked by database triggers and ORM listeners. |
| **10** | Failure & Rollback | `tests/test_security_attacks.py` | Simulated crash between debit and credit triggers complete rollback; zero orphaned records. |
| **11** | Statement Accuracy | `tests/test_statements.py` | Chronological debits, credits, and resulting running balances verified against ledger. |
| **12** | Deposit/Withdrawal Accounting | `tests/test_money_conservation.py` | External movements balanced against `SYSTEM_CLEARING` account preserving system equilibrium. |

### Mathematical Invariant & Balance Integrity CLI Verification

Run the real-time invariant verifier to validate all accounts, double-entry equilibrium, and money conservation:

```bash
cd backend
python -m app.verify_system
```

Expected Output:
```
======================================================================
 🛡️  LEDGERLINE FINANCIAL INTEGRITY & MATHEMATICAL INVARIANT AUDIT
======================================================================
[1/5] Testing Database Connectivity...
  ✅ Database connection: OK (PostgreSQL ACID operational)

[2/5] Validating Double-Entry Equilibrium (Σ Debits == Σ Credits)...
  • Discrepancy  : ₹0.0000
  ✅ Mathematical Equilibrium: PERFECT (Discrepancy is exactly ₹0.0000)

[3/5] Validating Conservation of Money across all Accounts...
  • Net System Balance (User Accounts + Clearing): ₹0.0000
  ✅ Conservation of Money: PERFECT (Total system balance is ₹0.0000)

[4/5] Checking for Negative Balances on User Accounts...
  ✅ Non-Negative Balance Invariant: PERFECT (0 accounts below zero)

[5/5] Auditing Transaction Header to Ledger Entry Pairing...
  ✅ All Transactions: BALANCED (100% of journals contain equal debits and credits)
======================================================================
 🌟 AUDIT CERTIFICATE: LEDGERLINE SYSTEM IS MATHEMATICALLY SOUND
======================================================================
```

---

## 7. Deployment Architecture

| Tier | Provider | Service Type | Build / Start Command | Public Endpoint |
|---|---|---|---|---|
| **Frontend** | Vercel | Single-Page App (React + Vite) | `npm run build` | `https://ledgerline.vercel.app` (Pending deployment) |
| **Backend** | Render | Web Service (FastAPI) | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `https://ledgerline-api.onrender.com` (Pending deployment) |
| **Database** | Render | Managed PostgreSQL 16 | Auto-managed | Render Internal / External connection |

---

## 8. Known Limitations & Production Roadmap

1. **Cross-Currency Currency Conversion:** Currently, transfers require both accounts to share the same ISO 4217 currency. Cross-currency settlements will require an automated FX rate service and treasury conversion ledger.
2. **Idempotency Key Retention Policy:** In high-volume production, `idempotency_records` must be partitioned or pruned by a scheduled background worker for records older than 30 days.
3. **Database Read Replicas:** Large auditor reconciliation queries on multi-million row datasets should be routed to a read replica to prevent connection contention on the write primary.

---

## 9. Comprehensive Documentation Index

- [**`docs/THREATS.md`**](docs/THREATS.md) – In-depth threat model detailing 15 attack scenarios, mitigations, and verifying tests.
- [**`docs/PROMPTS.md`**](docs/PROMPTS.md) – Dated AI prompt and development audit log with commit references.
- [**`docs/DATABASE_SCHEMA.md`**](docs/DATABASE_SCHEMA.md) – Complete DDL, constraints, indexes, triggers, and accounting ER diagram.
- [**`docs/API_DOCUMENTATION.md`**](docs/API_DOCUMENTATION.md) – OpenAPI endpoint specifications, request/response schemas, and error codes.
- [**`docs/DEPLOYMENT.md`**](docs/DEPLOYMENT.md) – Step-by-step production deployment guide for Render and Vercel.
- [**`.env.example`**](.env.example) – Sanitized configuration template.
