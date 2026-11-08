# LedgerLine Production Deployment Guide

This guide walks through deploying LedgerLine to production using **Render** (PostgreSQL & FastAPI Backend) and **Vercel** (React Frontend).

---

## Architecture Overview

```mermaid
graph LR
    Client[Web Browser] -->|HTTPS| Vercel[Vercel: React + Vite SPA]
    Vercel -->|REST API / JSON| RenderAPI[Render: FastAPI Backend]
    RenderAPI -->|Asyncpg / SSL| RenderDB[(Render: PostgreSQL 16)]
```

---

## 1. 1-Click Cloud Deployment (Render Blueprint via `render.yaml`)

The repository includes a production-ready `render.yaml` blueprint. Render will automatically spin up PostgreSQL 16 and the FastAPI Web Service, run Alembic migrations, and wire the database credentials in one click.

1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** &rarr; **Blueprint**.
3. Select your GitHub repository: `https://github.com/prudhvi5273/ledgerline`.
4. Render detects `render.yaml` and provisions:
   - **Database:** `ledgerline-db` (PostgreSQL 16)
   - **Backend Service:** `ledgerline-backend` (FastAPI + Python 3)
   - **Pre-deploy Hook:** `alembic upgrade head`
   - **Health Check:** `/health`
5. Click **Apply**.
6. Once deployed, test the live health endpoint:  
   👉 `https://<your-render-subdomain>.onrender.com/health`  
   Expected response:
   ```json
   {
     "status": "UP",
     "app": "LedgerLine",
     "version": "1.0.0",
     "database": "HEALTHY"
   }
   ```
   Interactive OpenAPI / Swagger documentation will be live at `https://<your-render-subdomain>.onrender.com/docs`.

---

## 2. Manual Backend Deployment (Alternative)

1. In Render Dashboard, click **New +** &rarr; **Web Service**.
2. Connect your GitHub repository: `https://github.com/prudhvi5273/ledgerline`.
3. Configure Web Service settings:
   - **Name:** `ledgerline-backend`
   - **Region:** Same region as your database.
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** Free

4. Configure **Environment Variables** in Render:
   | Key | Value / Description |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `False` |
   | `DATABASE_URL` | `postgresql+asyncpg://<user>:<password>@<internal-host>/ledgerline_db` |
   | `SYNC_DATABASE_URL` | `postgresql+psycopg://<user>:<password>@<internal-host>/ledgerline_db` |
   | `JWT_SECRET_KEY` | Generate with `openssl rand -hex 32` |
   | `CORS_ORIGINS` | `https://ledgerline.vercel.app,http://localhost:5173` |

5. Click **Create Web Service**.
6. When deployment finishes, test the live health check:  
   👉 `https://ledgerline-backend.onrender.com/health`  
   Expected JSON response:
   ```json
   {
     "status": "UP",
     "app": "LedgerLine",
     "version": "1.0.0",
     "database": "HEALTHY"
   }
   ```

---

## 3. Frontend Deployment (Vercel)

1. Log into your [Vercel Dashboard](https://vercel.com/).
2. Click **Add New...** &rarr; **Project**.
3. Import your GitHub repository: `prudhvi5273/ledgerline`.
4. Configure Project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`
5. Configure **Environment Variables** in Vercel:
   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://ledgerline-backend.onrender.com/api/v1` |
6. Click **Deploy**.

---

## 4. Post-Deployment Verification Checklist

Once both services are deployed, verify in a private/incognito window:

- [ ] **1. Public Health Check:** Open `/health` on the backend URL. Assert `database: "HEALTHY"`.
- [ ] **2. Client Login:** Sign in with `client.alice@example.com` / `SecretPassword123!`.
- [ ] **3. Account Creation:** Open an account in USD or INR.
- [ ] **4. Deposit Funds:** Deposit ₹5,000. Verify balance updates instantly.
- [ ] **5. Idempotent Transfer:** Transfer ₹1,000 to another account. Click submit twice or check network to verify only one transaction executes.
- [ ] **6. Overdraft Prevention:** Attempt to withdraw more than available balance. Assert refusal.
- [ ] **7. Auditor Role:** Sign in with `auditor.check@example.com` / `AuditorPass123!`. Open Auditor Portal and verify that total debits equal total credits with ₹0.0000 discrepancy.
- [ ] **8. Admin Role:** Sign in with `admin.root@example.com` / `AdminMasterPass123!`. Verify freeze and unfreeze toggles.
