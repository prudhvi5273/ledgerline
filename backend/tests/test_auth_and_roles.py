from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.user import User
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_unauthorized_account_transfer_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    client_bob: User
):
    """
    TEST 7: UNAUTHORIZED TRANSFER
    User A attempts to transfer money from User B's account.
    Verify rejection with HTTP 403 and zero financial postings.
    """
    # Bob owns account with funds
    acc_bob = Account(
        user_id=client_bob.id,
        account_number="ACC-BOB-SAFE",
        currency="INR",
        balance=Decimal("2000.0000"),
        status="ACTIVE"
    )
    # Alice owns destination
    acc_alice = Account(
        user_id=client_user.id,
        account_number="ACC-ALICE-DEST",
        currency="INR",
        balance=Decimal("100.0000"),
        status="ACTIVE"
    )
    db_session.add_all([acc_bob, acc_alice])
    await db_session.commit()
    await db_session.refresh(acc_bob)
    await db_session.refresh(acc_alice)

    # Alice attempts to transfer FROM Bob's account using Alice's JWT token
    headers = {
        **get_auth_headers(client_user),  # Alice's token
        "Idempotency-Key": str(uuid.uuid4())
    }
    malicious_payload = {
        "source_account_id": str(acc_bob.id),  # Bob's account!
        "destination_account_id": str(acc_alice.id),
        "amount": "500.00",
        "description": "Unauthorized theft attempt"
    }

    response = await client.post("/api/v1/transactions/transfer", json=malicious_payload, headers=headers)
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()

    # Verify no funds moved
    await db_session.refresh(acc_bob)
    await db_session.refresh(acc_alice)
    assert acc_bob.balance == Decimal("2000.0000"), "Bob's balance must not change"
    assert acc_alice.balance == Decimal("100.0000"), "Alice's balance must not change"


@pytest.mark.asyncio
async def test_auditor_cannot_execute_financial_transactions(
    client: AsyncClient,
    db_session: AsyncSession,
    auditor_user: User,
    client_user: User
):
    """
    TEST 8: AUDITOR ACCESS
    Attempt to deposit, withdraw or transfer using auditor credentials.
    Verify all money-moving operations are strictly denied.
    """
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-AUDIT-TARGET",
        currency="INR",
        balance=Decimal("1000.0000"),
        status="ACTIVE"
    )
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    auditor_headers = {
        **get_auth_headers(auditor_user),
        "Idempotency-Key": str(uuid.uuid4())
    }

    # 1. Attempt Deposit as Auditor
    dep_res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": str(acc.id), "amount": "100.00"},
        headers=auditor_headers
    )
    assert dep_res.status_code == 403
    assert "read-only" in dep_res.json()["detail"].lower()

    # 2. Attempt Withdrawal as Auditor
    wth_res = await client.post(
        "/api/v1/transactions/withdraw",
        json={"account_id": str(acc.id), "amount": "100.00"},
        headers=auditor_headers
    )
    assert wth_res.status_code == 403
    assert "read-only" in wth_res.json()["detail"].lower()

    # 3. Attempt Transfer as Auditor
    trf_res = await client.post(
        "/api/v1/transactions/transfer",
        json={
            "source_account_id": str(acc.id),
            "destination_account_id": str(acc.id),
            "amount": "100.00"
        },
        headers=auditor_headers
    )
    assert trf_res.status_code == 403
    assert "read-only" in trf_res.json()["detail"].lower()
