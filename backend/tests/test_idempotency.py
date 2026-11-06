from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import LedgerTransaction
from app.models.user import User
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_idempotency_same_key_returns_cached_response(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    client_bob: User
):
    """
    TEST 3: IDEMPOTENCY
    Submit the same transfer request twice with the same idempotency key.
    Verify only one financial transaction is created and identical response returned.
    """
    acc_src = Account(
        user_id=client_user.id,
        account_number="ACC-IDEMP-SRC",
        currency="INR",
        balance=Decimal("1000.0000"),
        status="ACTIVE"
    )
    acc_dst = Account(
        user_id=client_bob.id,
        account_number="ACC-IDEMP-DST",
        currency="INR",
        balance=Decimal("500.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_src, acc_dst])
    await db_session.commit()
    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)

    shared_key = str(uuid.uuid4())
    headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": shared_key
    }
    payload = {
        "source_account_id": str(acc_src.id),
        "destination_account_id": str(acc_dst.id),
        "amount": "300.00",
        "description": "Idempotent payment"
    }

    # Request 1
    res1 = await client.post("/api/v1/transactions/transfer", json=payload, headers=headers)
    assert res1.status_code == 201
    body1 = res1.json()

    # Request 2 (Identical key & payload)
    res2 = await client.post("/api/v1/transactions/transfer", json=payload, headers=headers)
    assert res2.status_code == 201
    body2 = res2.json()

    # Assert response bodies match exactly
    assert body1["id"] == body2["id"]
    assert body1["reference_id"] == body2["reference_id"]
    assert body1["total_amount"] == body2["total_amount"]

    # Verify database has only ONE transaction
    tx_count_stmt = select(func.count(LedgerTransaction.id)).where(
        LedgerTransaction.reference_id == body1["reference_id"]
    )
    tx_count = (await db_session.execute(tx_count_stmt)).scalar_one()
    assert tx_count == 1, "Exactly one transaction must exist in the database"

    # Verify account balance was only deducted ONCE (1000 - 300 = 700, NOT 400)
    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)
    assert acc_src.balance == Decimal("700.0000")
    assert acc_dst.balance == Decimal("800.0000")


@pytest.mark.asyncio
async def test_idempotency_different_payload_returns_conflict(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    client_bob: User
):
    """
    TEST 4: DIFFERENT PAYLOAD WITH SAME KEY
    Reuse the same idempotency key with a different amount or destination.
    Verify a 409 Conflict response and no additional transfer.
    """
    acc_src = Account(
        user_id=client_user.id,
        account_number="ACC-CONFLICT-SRC",
        currency="INR",
        balance=Decimal("1000.0000"),
        status="ACTIVE"
    )
    acc_dst = Account(
        user_id=client_bob.id,
        account_number="ACC-CONFLICT-DST",
        currency="INR",
        balance=Decimal("500.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_src, acc_dst])
    await db_session.commit()
    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)

    shared_key = str(uuid.uuid4())
    headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": shared_key
    }
    payload1 = {
        "source_account_id": str(acc_src.id),
        "destination_account_id": str(acc_dst.id),
        "amount": "100.00",
        "description": "Original transfer"
    }

    # First request succeeds
    res1 = await client.post("/api/v1/transactions/transfer", json=payload1, headers=headers)
    assert res1.status_code == 201

    # Second request with SAME key but DIFFERENT amount (500 instead of 100)
    payload2 = {
        "source_account_id": str(acc_src.id),
        "destination_account_id": str(acc_dst.id),
        "amount": "500.00",
        "description": "Reused key with modified amount"
    }
    res2 = await client.post("/api/v1/transactions/transfer", json=payload2, headers=headers)
    assert res2.status_code == 409, "Must return HTTP 409 Conflict"
    assert "different request payload" in res2.json()["detail"]

    # Verify balance was only debited ₹100, not ₹600
    await db_session.refresh(acc_src)
    assert acc_src.balance == Decimal("900.0000")
