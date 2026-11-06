from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.ledger_entry import LedgerEntry
from app.models.user import User
from app.schemas.audit import AuditLogResponse, ReconciliationReport

router = APIRouter(prefix="/auditor", tags=["Auditor Portal"])


@router.get("/reconciliation", response_model=ReconciliationReport)
async def get_ledger_reconciliation(
    auditor_user: User = Depends(require_role(["AUDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Independent verification of ledger equilibrium.
    Verifies that:
    1. Sum of all debits equals sum of all credits across all ledger entries.
    2. Sum of all user balances + system clearing balance equals zero (conservation of funds).
    """
    # 1. Total debits
    stmt_debit = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(
        LedgerEntry.entry_type == "DEBIT"
    )
    total_debits = (await db.execute(stmt_debit)).scalar_one()

    # 2. Total credits
    stmt_credit = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(
        LedgerEntry.entry_type == "CREDIT"
    )
    total_credits = (await db.execute(stmt_credit)).scalar_one()

    # 3. User balances
    stmt_user_balance = select(func.coalesce(func.sum(Account.balance), Decimal("0.0000"))).where(
        Account.account_type != "SYSTEM_CLEARING"
    )
    total_user_balance = (await db.execute(stmt_user_balance)).scalar_one()

    # 4. Clearing balance
    stmt_clearing = select(func.coalesce(func.sum(Account.balance), Decimal("0.0000"))).where(
        Account.account_type == "SYSTEM_CLEARING"
    )
    clearing_balance = (await db.execute(stmt_clearing)).scalar_one()

    # 5. Total accounts
    stmt_count = select(func.count(Account.id))
    total_accounts = (await db.execute(stmt_count)).scalar_one()

    total_system_balance = total_user_balance + clearing_balance
    discrepancy = abs(total_debits - total_credits)
    is_balanced = (discrepancy == Decimal("0.0000")) and (total_system_balance == Decimal("0.0000"))

    return ReconciliationReport(
        total_accounts=total_accounts,
        total_user_balance=total_user_balance,
        system_clearing_balance=clearing_balance,
        total_system_balance=total_system_balance,
        total_ledger_debits=total_debits,
        total_ledger_credits=total_credits,
        is_balanced=is_balanced,
        discrepancy=discrepancy,
        checked_at=datetime.now(timezone.utc)
    )


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auditor_user: User = Depends(require_role(["AUDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Auditor-only: Inspect tamper-evident audit records and refused transactions."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
