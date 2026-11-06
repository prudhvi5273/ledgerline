from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_money_conservation_transfer(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    client_bob: User
):
    """
    TEST 1: MONEY CONSERVATION
    Transfer ₹1,000 between two accounts.
    Verify that sender loses ₹1,000 and receiver gains ₹1,000.
    Verify total debits strictly equal total credits.
    """
    # 1. Setup accounts
    acc_alice = Account(
        user_id=client_user.id,
        account_number="ACC-ALICE-01",
        currency="INR",
        balance=Decimal("5000.0000"),
        status="ACTIVE"
    )
    acc_bob = Account(
        user_id=client_bob.id,
        account_number="ACC-BOB-01",
        currency="INR",
        balance=Decimal("2000.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_alice, acc_bob])
    await db_session.commit()
    await db_session.refresh(acc_alice)
    await db_session.refresh(acc_bob)

    initial_total = acc_alice.balance + acc_bob.balance  # ₹7,000

    # 2. Execute Transfer via API
    transfer_amount = Decimal("1000.0000")
    idemp_key = str(uuid.uuid4())
    headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": idemp_key
    }
    payload = {
        "source_account_id": str(acc_alice.id),
        "destination_account_id": str(acc_bob.id),
        "amount": "1000.00",
        "description": "Test conservation transfer"
    }

    response = await client.post("/api/v1/transactions/transfer", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["total_amount"] == "1000.0000"

    # 3. Refresh balances from DB
    await db_session.refresh(acc_alice)
    await db_session.refresh(acc_bob)

    assert acc_alice.balance == Decimal("4000.0000"), "Sender must lose exactly ₹1,000"
    assert acc_bob.balance == Decimal("3000.0000"), "Receiver must gain exactly ₹1,000"
    assert acc_alice.balance + acc_bob.balance == initial_total, "Total money in system must remain conserved"

    # 4. Verify Double-Entry Ledger Equilibrium
    tx_id = uuid.UUID(data["id"])
    stmt_entries = select(LedgerEntry).where(LedgerEntry.transaction_id == tx_id)
    entries = (await db_session.execute(stmt_entries)).scalars().all()

    assert len(entries) == 2, "Transfer must generate exactly 2 balanced ledger entries"
    debit_entry = next(e for e in entries if e.entry_type == "DEBIT")
    credit_entry = next(e for e in entries if e.entry_type == "CREDIT")

    assert debit_entry.account_id == acc_alice.id
    assert debit_entry.amount == transfer_amount
    assert credit_entry.account_id == acc_bob.id
    assert credit_entry.amount == transfer_amount
    assert debit_entry.amount == credit_entry.amount, "Debits must strictly equal Credits"


@pytest.mark.asyncio
async def test_external_deposit_and_withdrawal_accounting(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User
):
    """
    TEST 12: DEPOSIT AND WITHDRAWAL ACCOUNTING
    Verify that external movements are recorded against system clearing accounts
    and strictly conserve the accounting equation.
    """
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-ALICE-CLEARING",
        currency="INR",
        balance=Decimal("0.0000"),
        status="ACTIVE"
    )
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    # 1. Deposit ₹2,500
    dep_headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": str(uuid.uuid4())
    }
    dep_payload = {
        "account_id": str(acc.id),
        "amount": "2500.00",
        "description": "Initial deposit"
    }
    dep_res = await client.post("/api/v1/transactions/deposit", json=dep_payload, headers=dep_headers)
    assert dep_res.status_code == 201

    await db_session.refresh(acc)
    assert acc.balance == Decimal("2500.0000")

    # Verify double-entry on deposit
    dep_tx_id = uuid.UUID(dep_res.json()["id"])
    dep_entries = (await db_session.execute(
        select(LedgerEntry).where(LedgerEntry.transaction_id == dep_tx_id)
    )).scalars().all()

    assert len(dep_entries) == 2
    sum_debits = sum(e.amount for e in dep_entries if e.entry_type == "DEBIT")
    sum_credits = sum(e.amount for e in dep_entries if e.entry_type == "CREDIT")
    assert sum_debits == sum_credits == Decimal("2500.0000")

    # 2. Withdraw ₹1,000
    wth_headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": str(uuid.uuid4())
    }
    wth_payload = {
        "account_id": str(acc.id),
        "amount": "1000.00",
        "description": "ATM withdrawal"
    }
    wth_res = await client.post("/api/v1/transactions/withdraw", json=wth_payload, headers=wth_headers)
    assert wth_res.status_code == 201

    await db_session.refresh(acc)
    assert acc.balance == Decimal("1500.0000")

    wth_tx_id = uuid.UUID(wth_res.json()["id"])
    wth_entries = (await db_session.execute(
        select(LedgerEntry).where(LedgerEntry.transaction_id == wth_tx_id)
    )).scalars().all()

    assert len(wth_entries) == 2
    w_debits = sum(e.amount for e in wth_entries if e.entry_type == "DEBIT")
    w_credits = sum(e.amount for e in wth_entries if e.entry_type == "CREDIT")
    assert w_debits == w_credits == Decimal("1000.0000")
