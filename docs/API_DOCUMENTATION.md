# LedgerLine REST API Documentation

This document specifies all REST API endpoints provided by the LedgerLine backend, their authentication requirements, permitted roles, request payloads, response bodies, and HTTP status codes.

Interactive Swagger/OpenAPI documentation is available at:  
👉 **`http://localhost:8000/docs`** (or your live Render backend URL).

---

## 1. Authentication Endpoints

### 1.1 `POST /api/v1/auth/register`
- **Purpose:** Public self-registration for new users.
- **Permitted Roles:** Public (Unauthenticated).
- **Security Rule:** Always assigns role `ACCOUNT_HOLDER`.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecretPassword123!",
    "full_name": "Alice Smith"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "email": "user@example.com",
    "full_name": "Alice Smith",
    "role": "ACCOUNT_HOLDER",
    "is_active": true,
    "created_at": "2026-11-07T12:00:00Z"
  }
  ```

### 1.2 `POST /api/v1/auth/login`
- **Purpose:** Authenticate credentials and receive signed JWT tokens.
- **Permitted Roles:** Public (Unauthenticated).
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecretPassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

### 1.3 `POST /api/v1/auth/refresh`
- **Purpose:** Refresh an expired access token using a valid refresh token.
- **Request Body:**
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response (200 OK):** New access and refresh token pair.

### 1.4 `GET /api/v1/auth/me`
- **Purpose:** Retrieve profile information of the currently authenticated user.
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):** User details object.

---

## 2. Settlement Accounts Endpoints

### 2.1 `POST /api/v1/accounts`
- **Purpose:** Open a new banking account.
- **Permitted Roles:** `ACCOUNT_HOLDER`, `ADMIN` (Auditors are rejected).
- **Request Body:**
  ```json
  {
    "currency": "INR",
    "account_type": "USER_CHECKING"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "user_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "account_number": "100849204918",
    "currency": "INR",
    "balance": "0.0000",
    "status": "ACTIVE",
    "account_type": "USER_CHECKING",
    "created_at": "2026-11-07T12:00:00Z"
  }
  ```

### 2.2 `GET /api/v1/accounts`
- **Purpose:** List accounts. Account holders view own accounts; Admins and Auditors view all accounts.
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):** Array of account objects.

### 2.3 `GET /api/v1/accounts/{account_id}`
- **Purpose:** Retrieve account details by ID with ownership verification.
- **Response (200 OK):** Account object.

### 2.4 `GET /api/v1/accounts/{account_id}/balance`
- **Purpose:** Query authoritative ledger balance.
- **Response (200 OK):**
  ```json
  {
    "account_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "account_number": "100849204918",
    "currency": "INR",
    "balance": "5000.0000",
    "status": "ACTIVE",
    "as_of": "2026-11-07T12:00:00Z"
  }
  ```

---

## 3. Money Movement Endpoints

All money-moving endpoints require an `Idempotency-Key` header.

### 3.1 `POST /api/v1/transactions/transfer`
- **Purpose:** Execute internal transfer between two accounts with double-entry recording and deterministic row locking.
- **Headers:** 
  - `Authorization: Bearer <token>`
  - `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "source_account_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "destination_account_id": "f1e2d3c4-b5a6-7f8e-9d0c-1b2a3f4e5d6c",
    "amount": "1000.00",
    "description": "Invoice payment"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "reference_id": "TX-TRF-A1B2C3D4E5F6",
    "transaction_type": "TRANSFER",
    "status": "POSTED",
    "description": "Invoice payment",
    "total_amount": "1000.0000",
    "currency": "INR",
    "created_at": "2026-11-07T12:00:00Z",
    "entries": [
      {
        "id": "e1...",
        "transaction_id": "a1...",
        "account_id": "e5...",
        "entry_type": "DEBIT",
        "amount": "1000.0000",
        "balance_after": "4000.0000",
        "created_at": "2026-11-07T12:00:00Z"
      },
      {
        "id": "e2...",
        "transaction_id": "a1...",
        "account_id": "f1...",
        "entry_type": "CREDIT",
        "amount": "1000.0000",
        "balance_after": "3000.0000",
        "created_at": "2026-11-07T12:00:00Z"
      }
    ]
  }
  ```
- **Error Codes:**
  - `400 Bad Request`: Insufficient funds, identical source and destination accounts, or negative amount.
  - `403 Forbidden`: User does not own source account, or account is frozen.
  - `409 Conflict`: Reused idempotency key with modified payload or concurrent in-flight request.

### 3.2 `POST /api/v1/transactions/deposit`
- **Purpose:** External funds deposit credited to user account and debited to `SYSTEM_CLEARING`.
- **Headers:** `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "account_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "amount": "2500.00",
    "description": "Salary deposit"
  }
  ```
- **Response (201 Created):** Transaction receipt with balanced debit and credit entries.

### 3.3 `POST /api/v1/transactions/withdraw`
- **Purpose:** External funds withdrawal debited from user account and credited to `SYSTEM_CLEARING`.
- **Headers:** `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "account_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
    "amount": "500.00",
    "description": "ATM withdrawal"
  }
  ```
- **Response (201 Created):** Transaction receipt.

---

## 4. Statements & History Endpoints

### 4.1 `GET /api/v1/accounts/{account_id}/statement`
- **Purpose:** Chronological statement showing debits, credits, and continuous running balances.
- **Response (200 OK):**
  ```json
  {
    "account_id": "e5f6a7b8...",
    "account_number": "100849204918",
    "currency": "INR",
    "current_balance": "4500.0000",
    "total_debits": "500.0000",
    "total_credits": "5000.0000",
    "total_transactions": 2,
    "items": [
      {
        "entry_id": "...",
        "transaction_id": "...",
        "reference_id": "TX-DEP-...",
        "transaction_type": "DEPOSIT",
        "entry_type": "CREDIT",
        "amount": "5000.0000",
        "balance_after": "5000.0000",
        "description": "Initial deposit",
        "created_at": "..."
      }
    ]
  }
  ```

---

## 5. Administrative Endpoints

- `GET /api/v1/admin/users`: List all platform users (Admin only).
- `POST /api/v1/admin/users`: Provision privileged users with `ADMIN` or `AUDITOR` roles (Admin only).
- `GET /api/v1/admin/accounts`: List all system and user accounts (Admin only).
- `PATCH /api/v1/admin/accounts/{account_id}/status`: Freeze or unfreeze an account (`ACTIVE`, `FROZEN`, `CLOSED`) (Admin only).
- `GET /api/v1/admin/audit-logs`: Inspect security and financial refusal events (Admin only).

---

## 6. Auditor Compliance Endpoints

- `GET /api/v1/auditor/reconciliation`: Reconciles the global ledger:
  - Asserts $\sum \text{Debits} == \sum \text{Credits}$.
  - Asserts $\text{User Balances} + \text{System Clearing Balance} == 0$.
  - Reports exact discrepancy (must be `0.0000`).
- `GET /api/v1/auditor/audit-logs`: Query tamper-evident audit logs with refusal filtering.
- `GET /api/v1/transactions`: Read-only transaction stream across the platform.
