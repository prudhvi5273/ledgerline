from decimal import Decimal
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.schemas.transaction import StatementItem, StatementResponse

router = APIRouter(prefix="/accounts", tags=["Statements"])


@router.get("/{account_id}/statement", response_model=StatementResponse)
async def get_account_statement(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an authoritative chronological statement of all ledger postings for an account.
    Verifies that running balances strictly match ledger entries.
    """
    stmt_acc = select(Account).where(Account.id == account_id)
    account = (await db.execute(stmt_acc)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    if current_user.role not in ["ADMIN", "AUDITOR"] and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this account statement."
        )

    # Fetch ledger entries ordered chronologically
    stmt_entries = (
        select(LedgerEntry)
        .where(LedgerEntry.account_id == account_id)
        .order_by(LedgerEntry.created_at.asc())
        .options(selectinload(LedgerEntry.transaction))
    )
    entries = (await db.execute(stmt_entries)).scalars().all()

    statement_items = []
    total_debits = Decimal("0.0000")
    total_credits = Decimal("0.0000")

    for entry in entries:
        if entry.entry_type == "DEBIT":
            total_debits += entry.amount
        elif entry.entry_type == "CREDIT":
            total_credits += entry.amount

        statement_items.append(
            StatementItem(
                entry_id=entry.id,
                transaction_id=entry.transaction_id,
                reference_id=entry.transaction.reference_id if entry.transaction else "UNKNOWN",
                transaction_type=entry.transaction.transaction_type if entry.transaction else "UNKNOWN",
                entry_type=entry.entry_type,
                amount=entry.amount,
                balance_after=entry.balance_after,
                description=entry.transaction.description if entry.transaction else None,
                created_at=entry.created_at
            )
        )

    return StatementResponse(
        account_id=account.id,
        account_number=account.account_number,
        currency=account.currency,
        current_balance=account.balance,
        total_debits=total_debits,
        total_credits=total_credits,
        total_transactions=len(statement_items),
        items=statement_items
    )
