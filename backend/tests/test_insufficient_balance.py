from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.user import User
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_insufficient_balance_withdrawal_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User
):
    """
    TEST 2: INSUFFICIENT BALANCE
    Attempt to withdraw more than the available balance.
    Verify rejection with HTTP 400 and unchanged financial balances.
    """
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-TEST-INSUFF-01",
        currency="INR",
        balance=Decimal("500.0000"),
        status="ACTIVE"
    )
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": str(uuid.uuid4())
    }
    # Request ₹600 with only ₹500 balance
    payload = {
        "account_id": str(acc.id),
        "amount": "600.00",
        "description": "Overdraft attempt"
    }

    response = await client.post("/api/v1/transactions/withdraw", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]

    # Balance must remain completely unchanged
    await db_session.refresh(acc)
    assert acc.balance == Decimal("500.0000")


@pytest.mark.asyncio
async def test_insufficient_balance_transfer_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    client_bob: User
):
    """Attempt to transfer more than available balance."""
    acc_src = Account(
        user_id=client_user.id,
        account_number="ACC-SRC-01",
        currency="INR",
        balance=Decimal("200.0000"),
        status="ACTIVE"
    )
    acc_dst = Account(
        user_id=client_bob.id,
        account_number="ACC-DST-01",
        currency="INR",
        balance=Decimal("100.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_src, acc_dst])
    await db_session.commit()
    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)

    headers = {
        **get_auth_headers(client_user),
        "Idempotency-Key": str(uuid.uuid4())
    }
    payload = {
        "source_account_id": str(acc_src.id),
        "destination_account_id": str(acc_dst.id),
        "amount": "200.01",
        "description": "Attempted overdraw transfer"
    }

    response = await client.post("/api/v1/transactions/transfer", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]

    await db_session.refresh(acc_src)
    await db_session.refresh(acc_dst)
    assert acc_src.balance == Decimal("200.0000")
    assert acc_dst.balance == Decimal("100.0000")
