from datetime import datetime, timezone
from decimal import Decimal
import random
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse, BalanceResponse
from app.services.audit_service import AuditService
from app.services.transfer_engine import TransferEngine

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def generate_unique_account_number() -> str:
    """Generate high-entropy 12-digit standard banking account number."""
    return f"100{random.randint(100000000, 999999999)}"


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Open a new banking account for the authenticated user."""
    # Auditors cannot create accounts
    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors have read-only access and cannot provision accounts."
        )

    # Loop to ensure account number uniqueness
    for _ in range(5):
        acc_num = generate_unique_account_number()
        stmt = select(Account).where(Account.account_number == acc_num)
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique account number. Please try again."
        )

    account = Account(
        user_id=current_user.id,
        account_number=acc_num,
        currency=payload.currency.upper(),
        balance=Decimal("0.0000"),
        status="ACTIVE",
        account_type=payload.account_type
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    await AuditService.log_event(
        db=db,
        actor_id=current_user.id,
        event_type="ACCOUNT_OPENED",
        status="SUCCESS",
        source_account_id=account.id,
        metadata_info={"account_number": account.account_number, "currency": account.currency}
    )
    await db.commit()

    return account


@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List accounts.
    Account holders view only their own accounts.
    If an onboarding user has no account yet, automatically provisions a primary checking account.
    Administrators and Auditors can view all system accounts.
    """
    if current_user.role in ["ADMIN", "AUDITOR"]:
        stmt = select(Account).where(Account.account_type != "SYSTEM_CLEARING").order_by(Account.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()
    else:
        stmt = select(Account).where(
            Account.user_id == current_user.id,
            Account.account_type != "SYSTEM_CLEARING"
        ).order_by(Account.created_at.desc())
        result = await db.execute(stmt)
        accounts = list(result.scalars().all())

        if not accounts:
            # Auto-provision primary checking account for new user
            acc_num = generate_unique_account_number()
            new_acc = Account(
                user_id=current_user.id,
                account_number=acc_num,
                currency="INR",
                balance=Decimal("0.0000"),
                status="ACTIVE",
                account_type="USER_CHECKING"
            )
            db.add(new_acc)
            await db.commit()
            await db.refresh(new_acc)

            # Auto-fund with 25,000 INR welcome grant so they can immediately test transfers & withdrawals
            try:
                await TransferEngine.execute_deposit(
                    db=db,
                    actor=current_user,
                    account_id=new_acc.id,
                    amount=Decimal("25000.0000"),
                    description="Welcome onboarding grant"
                )
                await db.commit()
                await db.refresh(new_acc)
            except Exception:
                pass

            return [new_acc]

        return accounts


@router.get("/recipients", response_model=List[AccountResponse])
async def list_recipient_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List peer destination accounts for transfers (excluding caller's own accounts and system clearing)."""
    stmt = (
        select(Account)
        .where(
            Account.user_id != current_user.id,
            Account.account_type != "SYSTEM_CLEARING",
            Account.status == "ACTIVE"
        )
        .order_by(Account.created_at.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account_details(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve details for a specific account with ownership validation."""
    stmt = select(Account).where(Account.id == account_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    # Ownership check
    if current_user.role not in ["ADMIN", "AUDITOR"] and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this account."
        )

    return account


@router.get("/{account_id}/balance", response_model=BalanceResponse)
async def get_account_balance(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve real-time authoritative ledger balance for an account."""
    stmt = select(Account).where(Account.id == account_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    if current_user.role not in ["ADMIN", "AUDITOR"] and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this account balance."
        )

    return BalanceResponse(
        account_id=account.id,
        account_number=account.account_number,
        currency=account.currency,
        balance=account.balance,
        status=account.status,
        as_of=datetime.now(timezone.utc)
    )
