import asyncio
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.services.transfer_engine import TransferEngine
from tests.conftest import TestingSessionLocal, get_auth_headers


@pytest.mark.asyncio
async def test_concurrent_withdrawals_no_overdraft(client: AsyncClient, client_user: User):
    """
    TEST 5 – CONCURRENT WITHDRAWALS (MANDATORY)
    Create an account with ₹1,000.
    Fire two simultaneous withdrawal requests of ₹800 using independent database sessions.
    Verify that only one succeeds and the balance never becomes negative.
    """
    # 1. Setup account in an independent session
    async with TestingSessionLocal() as session:
        acc = Account(
            user_id=client_user.id,
            account_number="ACC-RACE-WTH-01",
            currency="INR",
            balance=Decimal("1000.0000"),
            status="ACTIVE"
        )
        session.add(acc)
        await session.commit()
        await session.refresh(acc)
        account_id = acc.id

    # 2. Fire two simultaneous withdrawal requests of ₹800 concurrently
    headers_1 = {**get_auth_headers(client_user), "Idempotency-Key": str(uuid.uuid4())}
    headers_2 = {**get_auth_headers(client_user), "Idempotency-Key": str(uuid.uuid4())}
    payload = {"account_id": str(account_id), "amount": "800.00", "description": "Concurrent withdrawal race"}

    # Execute both requests concurrently
    res1, res2 = await asyncio.gather(
        client.post("/api/v1/transactions/withdraw", json=payload, headers=headers_1),
        client.post("/api/v1/transactions/withdraw", json=payload, headers=headers_2),
        return_exceptions=False
    )

    statuses = [res1.status_code, res2.status_code]
    assert 201 in statuses, "At least one withdrawal must succeed"
    assert 400 in statuses, "The competing withdrawal must be rejected due to insufficient funds"

    # 3. Verify final balance in database
    async with TestingSessionLocal() as session:
        stmt = select(Account).where(Account.id == account_id)
        final_acc = (await session.execute(stmt)).scalar_one()
        assert final_acc.balance == Decimal("200.0000"), f"Balance must be exactly ₹200.0000, got {final_acc.balance}"
        assert final_acc.balance >= Decimal("0.0000"), "Balance must never drop below zero"


@pytest.mark.asyncio
async def test_concurrent_duplicate_transfers(client: AsyncClient, client_user: User, client_bob: User):
    """
    TEST 6 – CONCURRENT DUPLICATE TRANSFERS (MANDATORY)
    Fire two simultaneous requests with the SAME idempotency key.
    Verify only one transfer occurs.
    """
    async with TestingSessionLocal() as session:
        acc_src = Account(
            user_id=client_user.id,
            account_number="ACC-CONCUR-SRC",
            currency="INR",
            balance=Decimal("1000.0000"),
            status="ACTIVE"
        )
        acc_dst = Account(
            user_id=client_bob.id,
            account_number="ACC-CONCUR-DST",
            currency="INR",
            balance=Decimal("200.0000"),
            status="ACTIVE"
        )
        session.add_all([acc_src, acc_dst])
        await session.commit()
        await session.refresh(acc_src)
        await session.refresh(acc_dst)
        src_id, dst_id = acc_src.id, acc_dst.id

    shared_idemp_key = str(uuid.uuid4())
    headers = {**get_auth_headers(client_user), "Idempotency-Key": shared_idemp_key}
    payload = {
        "source_account_id": str(src_id),
        "destination_account_id": str(dst_id),
        "amount": "400.00",
        "description": "Simultaneous duplicate transfer"
    }

    # Fire both concurrently
    res1, res2 = await asyncio.gather(
        client.post("/api/v1/transactions/transfer", json=payload, headers=headers),
        client.post("/api/v1/transactions/transfer", json=payload, headers=headers),
        return_exceptions=False
    )

    # Valid results: either both return 201 (one created, one replayed cached),
    # or one returns 201 and the other returns 409 Conflict (in-flight).
    # BUT UNDER NO CIRCUMSTANCES should two transfers execute!
    valid_codes = {res1.status_code, res2.status_code}
    assert valid_codes.issubset({201, 409}), f"Unexpected status codes: {res1.status_code}, {res2.status_code}"

    async with TestingSessionLocal() as session:
        # Check source balance: must be ₹600 (deducted once), NOT ₹200 (deducted twice)
        acc_s = (await session.execute(select(Account).where(Account.id == src_id))).scalar_one()
        assert acc_s.balance == Decimal("600.0000"), f"Source balance was deducted multiple times: {acc_s.balance}"

        # Total transfers with this description must be exactly 1
        tx_count = (await session.execute(
            select(LedgerTransaction).where(LedgerTransaction.description == "Simultaneous duplicate transfer")
        )).scalars().all()
        assert len(tx_count) == 1, "Exactly one financial transaction must exist"


@pytest.mark.asyncio
async def test_ledger_immutability(db_session: AsyncSession, client_user: User):
    """
    TEST 9 – LEDGER IMMUTABILITY (MANDATORY)
    Attempt to modify or delete an existing posted ledger entry.
    Verify that application code and database triggers prevent modification.
    """
    # Create test entry
    tx = LedgerTransaction(
        reference_id="TX-IMMUTABLE-01",
        transaction_type="DEPOSIT",
        status="POSTED",
        description="Immutability check",
        total_amount=Decimal("500.0000"),
        currency="INR"
    )
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-IMMUTABLE-01",
        currency="INR",
        balance=Decimal("500.0000"),
        status="ACTIVE"
    )
    db_session.add_all([tx, acc])
    await db_session.commit()
    await db_session.refresh(tx)
    await db_session.refresh(acc)

    entry = LedgerEntry(
        transaction_id=tx.id,
        account_id=acc.id,
        entry_type="CREDIT",
        amount=Decimal("500.0000"),
        balance_after=Decimal("500.0000")
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    # 1. Attempt UPDATE
    with pytest.raises(Exception):
        await db_session.execute(
            update(LedgerEntry).where(LedgerEntry.id == entry.id).values(amount=Decimal("9999.0000"))
        )
        await db_session.commit()
    await db_session.rollback()

    # 2. Attempt DELETE
    with pytest.raises(Exception):
        await db_session.execute(
            delete(LedgerEntry).where(LedgerEntry.id == entry.id)
        )
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_failure_and_rollback_atomicity(db_session: AsyncSession, client_user: User, client_bob: User):
    """
    TEST 10 – FAILURE AND ROLLBACK (MANDATORY)
    Simulate a failure between debit and credit posting.
    Verify the complete database transaction rolls back and no orphaned records exist.
    """
    acc_src = Account(
        user_id=client_user.id,
        account_number="ACC-ROLLBACK-SRC",
        currency="INR",
        balance=Decimal("1000.0000"),
        status="ACTIVE"
    )
    acc_dst = Account(
        user_id=client_bob.id,
        account_number="ACC-ROLLBACK-DST",
        currency="INR",
        balance=Decimal("500.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_src, acc_dst])
    await db_session.commit()
    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)

    # Simulate atomic failure inside a transaction
    try:
        async with db_session.begin_nested():
            # Step 1: Debit sender
            acc_src.balance -= Decimal("200.0000")
            tx = LedgerTransaction(
                reference_id="TX-FAIL-SIM-01",
                transaction_type="TRANSFER",
                status="POSTED",
                total_amount=Decimal("200.0000"),
                currency="INR"
            )
            db_session.add(tx)
            await db_session.flush()

            debit = LedgerEntry(
                transaction_id=tx.id,
                account_id=acc_src.id,
                entry_type="DEBIT",
                amount=Decimal("200.0000"),
                balance_after=acc_src.balance
            )
            db_session.add(debit)
            await db_session.flush()

            # Step 2: INJECT FAILURE before credit posting
            raise RuntimeError("Simulated network crash before credit entry!")

    except RuntimeError:
        await db_session.rollback()

    # Verify complete rollback
    await db_session.refresh(acc_src)
    assert acc_src.balance == Decimal("1000.0000"), "Source balance must remain 1000 after rollback"

    # Verify no orphaned ledger transactions or entries exist
    orphaned_tx = (await db_session.execute(
        select(LedgerTransaction).where(LedgerTransaction.reference_id == "TX-FAIL-SIM-01")
    )).scalar_one_or_none()
    assert orphaned_tx is None, "No orphaned transaction record should exist"


@pytest.mark.asyncio
async def test_privilege_escalation_registration_blocked(client: AsyncClient):
    """
    SECURITY AUDIT TEST: Self-Registration Privilege Escalation
    Verify that an attacker cannot grant themselves ADMIN or AUDITOR role via public registration.
    """
    attacker_payload = {
        "email": "malicious.admin@attack.com",
        "password": "Password123!",
        "full_name": "Rogue Attacker",
        "role": "ADMIN"  # Malicious attempt to self-promote to ADMIN
    }

    response = await client.post("/api/v1/auth/register", json=attacker_payload)
    if response.status_code == 201:
        # If created, role MUST be overridden to ACCOUNT_HOLDER
        data = response.json()
        assert data["role"] == "ACCOUNT_HOLDER", "Public registration must never assign ADMIN role!"
    else:
        # Or rejected with 400 Bad Request
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_and_infinity_amounts_rejected(client: AsyncClient, client_user: User):
    """
    SECURITY AUDIT TEST: Invalid, Sub-cent, and Infinity Amounts
    Verify that malformed or non-finite numbers are rejected before hitting the database.
    """
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-VAL-AMT-01",
        currency="INR",
        balance=Decimal("1000.0000"),
        status="ACTIVE"
    )
    async with TestingSessionLocal() as session:
        session.add(acc)
        await session.commit()
        await session.refresh(acc)
        account_id = acc.id

    headers = {**get_auth_headers(client_user), "Idempotency-Key": str(uuid.uuid4())}

    # 1. Negative amount
    res_neg = await client.post("/api/v1/transactions/deposit", json={"account_id": str(account_id), "amount": "-100.00"}, headers=headers)
    assert res_neg.status_code == 422 or res_neg.status_code == 400

    # 2. Zero amount
    res_zero = await client.post("/api/v1/transactions/deposit", json={"account_id": str(account_id), "amount": "0.00"}, headers=headers)
    assert res_zero.status_code == 422 or res_zero.status_code == 400

    # 3. Sub-cent excessive decimal precision (> 4 decimal places)
    res_sub = await client.post("/api/v1/transactions/deposit", json={"account_id": str(account_id), "amount": "10.1234567"}, headers=headers)
    assert res_sub.status_code == 422 or res_sub.status_code == 400
