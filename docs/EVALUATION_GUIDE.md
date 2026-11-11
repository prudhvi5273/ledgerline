# LedgerLine – Evaluator & Reviewer Guide

> **Snovasys Fresher Hiring Challenge 2026**  
> **Candidate:** Prudhvi ([@prudhvi5273](https://github.com/prudhvi5273))  
> **Repository:** [https://github.com/prudhvi5273/ledgerline](https://github.com/prudhvi5273/ledgerline)  
> **Stack:** Python FastAPI, PostgreSQL 16 (ACID + Row-level Locks), React 18, Vite, TypeScript, Tailwind CSS, Docker.

---

## 1. Quickstart: 3 Ways to Run and Evaluate

### Option A: 1-Command Full Stack (Recommended)
Prerequisites: Docker & Docker Compose.
```bash
git clone https://github.com/prudhvi5273/ledgerline.git
cd ledgerline
docker-compose up --build -d
```
- **React Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

*(Demo accounts for Alice, Bob, Root Admin, and Auditor are seeded automatically on first launch!)*

---

### Option B: Local Development
Prerequisites: Python 3.11+, Node.js 20+, PostgreSQL 16.

```bash
# 1. Backend
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate  |  Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev
# Live at http://localhost:5173
```

---

### Option C: 1-Click Cloud Deployment
- **Backend & Database on Render**: Connect repository and select **Blueprint** (`render.yaml`).
- **Frontend on Vercel**: Import repository root, set root directory to `frontend`, and configure `VITE_API_BASE_URL`.

---

## 2. Demo Seed Credentials

| Role | Email | Password | Scope & Primary Use Case |
|---|---|---|---|
| **Account Holder** | `client.alice@example.com` | `SecretPassword123!` | Standard banking: Transfers, deposits, withdrawals, statements, chatbot. |
| **Account Holder** | `client.bob@example.com` | `SecretPassword123!` | Counterparty account holder: Receives Alice's transfers. |
| **Administrator** | `admin.root@example.com` | `AdminMasterPass123!` | Full visibility, provision users, freeze/unfreeze accounts, system audit log. |
| **Auditor** | `auditor.check@example.com` | `AuditorPass123!` | Read-only compliance: Verify $\sum \text{Debits} == \sum \text{Credits}$, export signed audit pack. |

---

## 3. Mandatory Challenge Criteria Verification Matrix

| # | Challenge Requirement | Verification Flow | Test File / Command |
|:---:|---|---|---|
| **1** | **Double-Entry Equilibrium** | $\sum \text{Debits} == \sum \text{Credits}$ across all transactions | `pytest backend/tests/test_money_conservation.py` or `python -m app.verify_system` |
| **2** | **Insufficient Balance Overdraft Prevention** | Withdrawals exceeding balance rejected with 400 | `pytest backend/tests/test_insufficient_balance.py` |
| **3** | **Exact-Once Idempotency Replay** | Identical key replays 201 response with 1 transfer created | `pytest backend/tests/test_idempotency.py` |
| **4** | **Payload Mismatch Conflict** | Same key with altered amount returns 409 Conflict | `pytest backend/tests/test_idempotency.py` |
| **5** | **Concurrent Withdrawals Race Condition** | Two simultaneous ₹800 requests against ₹1,000 balance | `pytest backend/tests/test_security_attacks.py -k test_concurrent_withdrawal_race` |
| **6** | **Concurrent Duplicate Keys Race** | Simultaneous requests with identical key execute once | `pytest backend/tests/test_security_attacks.py -k test_concurrent_duplicate_idempotency_race` |
| **7** | **Unauthorized Transfer Rejection** | User transferring from another user's account rejected (403) | `pytest backend/tests/test_auth_and_roles.py` |
| **8** | **Auditor Read-Only Boundary** | Auditor attempting deposit, transfer, or withdrawal rejected (403) | `pytest backend/tests/test_auth_and_roles.py` |
| **9** | **Append-Only Immutability** | Database triggers block SQL `UPDATE` and `DELETE` on ledger | `pytest backend/tests/test_security_attacks.py -k test_ledger_immutability` |
| **10** | **Failure & Atomic Rollback** | Simulated crash rolls back debit and credit; zero orphans | `pytest backend/tests/test_security_attacks.py -k test_failure_rollback_atomicity` |
| **11** | **Statement Chronological Accuracy** | Debits, credits, and continuous running balances match | `pytest backend/tests/test_statements.py` |
| **12** | **Deposit/Withdrawal Conservation** | Balanced against `SYSTEM_CLEARING` account preserving equilibrium | `pytest backend/tests/test_money_conservation.py` |

---

## 4. Step-by-Step UI Evaluation Flows

### Flow 1: Client Onboarding & Fast Login
1. Open [http://localhost:3000](http://localhost:3000) (or `http://localhost:5173`).
2. On the **Login** screen, click the quick-fill pill **"Alice Client"**.
3. Click **"Sign In to LedgerLine"**.
4. You are directed to the **Fintech Dashboard** showing Alice's net worth, balance trajectory chart, and recent ledger entries.

### Flow 2: Money Transfer with Idempotency & Confirmation
1. Navigate to **Transfers** in the sidebar.
2. Select Source Account: `ACC-ALICE-INR-01` (Checking).
3. Select Destination Account: Bob's Account (`ACC-BOB-INR-01`).
4. Notice the automatically generated **Idempotency-Key** (UUID v4) displayed on screen.
5. Enter Amount: `₹500.00`.
6. Click **"Review & Confirm Transfer"**. A modal displays the source, destination, exact amount, and warns about non-reversible ledger postings.
7. Click **"Execute Transfer"**.
8. A double-entry transaction receipt appears with:
   - Debit line item: Alice balance reduced.
   - Credit line item: Bob balance increased.
   - Authoritative Reference ID (e.g. `TX-TRF-XXXXXXXX`).

### Flow 3: Overdraft Prevention
1. Go to **Withdrawal** in the sidebar.
2. Select an account with balance ₹5,000.
3. Attempt to withdraw `₹10,000.00`.
4. Submit the request.
5. **Outcome:** The transaction is refused immediately with HTTP 400: *"Insufficient funds. Account balance is ₹5,000.0000, requested ₹10,000.0000"*.
6. Check the account balance: It remains unchanged at ₹5,000.00.

### Flow 4: Chronological Account Statements & CSV Export
1. Navigate to **Statements**.
2. Select account `ACC-ALICE-INR-01`.
3. View the statement table: Every row displays Posting Date, Reference ID, Debit/Credit indicator, Description, and continuous **Running Balance**.
4. Click **"Export CSV"**: Downloads `statement-ACC-ALICE-INR-01.csv` containing all ledger lines.
5. Click **"Print / Export PDF"**: Formatted print-ready layout with sensitive controls stripped out.

### Flow 5: Auditor Independent Reconciliation Portal
1. Click **Log Out** in the sidebar.
2. Click the **"Read-Only Auditor"** login pill and sign in (`auditor.check@example.com`).
3. The dashboard alerts: *"Auditor session active: Server-side RBAC dependencies prevent modifying, creating, or deleting accounts, transfers, or entries"*.
4. Inspect the **Reconciliation Card**:
   - Total Ledger Debits: ₹25,000.0000
   - Total Ledger Credits: ₹25,000.0000
   - **Discrepancy: ₹0.0000 (MATHEMATICALLY PROVEN & BALANCED)**
   - Total System Balance (Users + System Clearing): ₹0.0000
5. Click **"Export Audit Pack"**: Downloads a regulatory JSON bundle signed with an authoritative **SHA-256 payload checksum**.

### Flow 6: Administrator User & Account Controls
1. Log out and sign in as **"System Admin"** (`admin.root@example.com`).
2. Go to **Admin Portal**.
3. View all registered users across the platform.
4. Toggle account status to **"FROZEN"** for an account.
5. Log back in as that user and attempt a transfer: The transaction is rejected with HTTP 403: *"Account is frozen"*.

### Flow 7: AI Financial & Architectural Assistant (Chatbot)
1. On any screen, click the glowing AI bot bubble in the bottom right corner.
2. Select quick prompts or ask arbitrary questions:
   - *"How does row locking prevent double-spending?"*
   - *"Explain the Auditor reconciliation equation."*
   - *"How does double-entry work in LedgerLine?"*
3. The AI assistant responds in real-time with precise architectural explanations.

---

## 5. Automated CLI Audits & Benchmarks

Run these commands inside the `backend/` directory to run automated verification:

```bash
# 1. Full Pytest Test Suite (All 12 criteria + security attacks)
pytest -v

# 2. Real-Time Mathematical Invariant Audit
python -m app.verify_system

# 3. High-Concurrency Stress Benchmark (50 bidirectional transfers + 20 duplicate key races)
python -m app.stress_test
```

---

## 6. Postman & API Exploration

- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Pre-configured Postman Collection**: [`docs/LedgerLine.postman_collection.json`](docs/LedgerLine.postman_collection.json)
- **OpenAPI 3.1 Specification**: [`docs/openapi.json`](docs/openapi.json)
