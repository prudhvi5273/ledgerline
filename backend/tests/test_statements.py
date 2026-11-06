from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.user import User
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_statement_accuracy_and_running_balance(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User
):
    """
    TEST 11: STATEMENT ACCURACY
    Verify every statement entry and resulting running balance against the ledger.
    """
    acc = Account(
        user_id=client_user.id,
        account_number="ACC-STMT-TEST",
        currency="INR",
        balance=Decimal("0.0000"),
        status="ACTIVE"
    )
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    headers = get_auth_headers(client_user)

    # 1. Deposit ₹1,000 -> Running Balance: ₹1,000
    await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": str(acc.id), "amount": "1000.00", "description": "Paycheck"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())}
    )

    # 2. Deposit ₹500 -> Running Balance: ₹1,500
    await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": str(acc.id), "amount": "500.00", "description": "Bonus"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())}
    )

    # 3. Withdraw ₹300 -> Running Balance: ₹1,200
    await client.post(
        "/api/v1/transactions/withdraw",
        json={"account_id": str(acc.id), "amount": "300.00", "description": "Groceries"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())}
    )

    # Fetch statement
    stmt_res = await client.get(f"/api/v1/accounts/{acc.id}/statement", headers=headers)
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()

    assert stmt_data["total_transactions"] == 3
    assert stmt_data["total_credits"] == "1500.0000"
    assert stmt_data["total_debits"] == "300.0000"
    assert stmt_data["current_balance"] == "1200.0000"

    items = stmt_data["items"]
    assert items[0]["entry_type"] == "CREDIT"
    assert items[0]["amount"] == "1000.0000"
    assert items[0]["balance_after"] == "1000.0000"

    assert items[1]["entry_type"] == "CREDIT"
    assert items[1]["amount"] == "500.0000"
    assert items[1]["balance_after"] == "1500.0000"

    assert items[2]["entry_type"] == "DEBIT"
    assert items[2]["amount"] == "300.0000"
    assert items[2]["balance_after"] == "1200.0000"
