from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.account import AccountResponse, AccountStatusUpdate
from app.schemas.audit import AuditLogResponse
from app.schemas.auth import UserRegister, UserResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def provision_privileged_user(
    payload: UserRegister,
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only: Provision a new user with any authorized role (ADMIN, AUDITOR, ACCOUNT_HOLDER)."""
    stmt = select(User).where(User.email == payload.email.lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists.")

    from app.core.security import get_password_hash
    user = User(
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role or "ACCOUNT_HOLDER",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await AuditService.log_event(
        db=db,
        actor_id=admin_user.id,
        event_type="USER_PROVISIONED_BY_ADMIN",
        status="SUCCESS",
        metadata_info={"email": user.email, "assigned_role": user.role}
    )
    await db.commit()
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only: Retrieve all registered users across the platform."""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/accounts", response_model=List[AccountResponse])
async def list_all_system_accounts(
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only: Retrieve all system and user accounts."""
    stmt = select(Account).order_by(Account.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/accounts/{account_id}/status", response_model=AccountResponse)
async def update_account_status(
    account_id: uuid.UUID,
    payload: AccountStatusUpdate,
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only: Freeze, unfreeze, or close an account."""
    stmt = select(Account).where(Account.id == account_id).with_for_update()
    account = (await db.execute(stmt)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    if account.account_type == "SYSTEM_CLEARING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System settlement clearing account status cannot be altered."
        )

    previous_status = account.status
    account.status = payload.status
    await db.commit()
    await db.refresh(account)

    await AuditService.log_event(
        db=db,
        actor_id=admin_user.id,
        event_type="ACCOUNT_STATUS_CHANGED",
        status="SUCCESS",
        source_account_id=account.id,
        metadata_info={
            "previous_status": previous_status,
            "new_status": payload.status,
            "account_number": account.account_number
        }
    )
    await db.commit()

    return account


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def view_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only: Inspect security, access, and financial audit events."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
