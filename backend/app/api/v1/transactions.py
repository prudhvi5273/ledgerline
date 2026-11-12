from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_required_idempotency_key
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.schemas.transaction import (
    DepositRequest,
    LedgerEntryResponse,
    TransactionResponse,
    TransferRequest,
    WithdrawRequest
)
from app.services.idempotency_service import IdempotencyService
from app.services.transfer_engine import TransferEngine

router = APIRouter(prefix="/transactions", tags=["Money Movement"])


def format_tx_response(tx: LedgerTransaction) -> TransactionResponse:
    """Format transaction and its balanced ledger entries for output."""
    raw_entries = []
    try:
        raw_entries = tx.entries or []
    except Exception:
        raw_entries = []

    return TransactionResponse(
        id=tx.id,
        reference_id=tx.reference_id,
        transaction_type=tx.transaction_type,
        status=tx.status,
        description=tx.description,
        total_amount=tx.total_amount,
        currency=tx.currency,
        created_at=tx.created_at,
        entries=[
            LedgerEntryResponse(
                id=entry.id,
                transaction_id=entry.transaction_id,
                account_id=entry.account_id,
                entry_type=entry.entry_type,
                amount=entry.amount,
                balance_after=entry.balance_after,
                created_at=entry.created_at
            )
            for entry in raw_entries
        ]
    )


@router.post("/deposit", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def deposit_funds(
    payload: DepositRequest,
    idempotency_key: str = Depends(get_required_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deposit external funds into a specified account with double-entry recording."""
    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors have read-only access and cannot deposit funds."
        )

    # 1. Idempotency Check & Reserve
    request_path = "/api/v1/transactions/deposit"
    payload_hash = IdempotencyService.compute_hash(payload.model_dump())
    cached = await IdempotencyService.check_or_reserve(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=request_path,
        payload_hash=payload_hash
    )
    if cached:
        status_code, body = cached
        return JSONResponse(status_code=status_code, content=body)

    # 2. Execute Deposit
    try:
        tx = await TransferEngine.execute_deposit(
            db=db,
            actor=current_user,
            account_id=payload.account_id,
            amount=payload.amount,
            description=payload.description,
            idempotency_key=idempotency_key
        )
        formatted = format_tx_response(tx)

        # 3. Update Idempotency status in the SAME transaction
        await IdempotencyService.record_success(
            db=db,
            idempotency_key=idempotency_key,
            response_code=status.HTTP_201_CREATED,
            response_body=formatted.model_dump(mode="json")
        )
        # ATOMIC COMMIT: Double-entry lines + Idempotency completion commit together
        await db.commit()
        return formatted

    except HTTPException as he:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=he.status_code,
            error_detail=he.detail
        )
        raise he
    except Exception as e:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_detail="Internal transfer processing error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction failed. Balance was not modified."
        ) from e


@router.post("/withdraw", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def withdraw_funds(
    payload: WithdrawRequest,
    idempotency_key: str = Depends(get_required_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Withdraw funds from an account with row-level balance locking and double-entry entries."""
    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors have read-only access and cannot withdraw funds."
        )

    # 1. Idempotency Check & Reserve
    request_path = "/api/v1/transactions/withdraw"
    payload_hash = IdempotencyService.compute_hash(payload.model_dump())
    cached = await IdempotencyService.check_or_reserve(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=request_path,
        payload_hash=payload_hash
    )
    if cached:
        status_code, body = cached
        return JSONResponse(status_code=status_code, content=body)

    # 2. Execute Withdrawal
    try:
        tx = await TransferEngine.execute_withdrawal(
            db=db,
            actor=current_user,
            account_id=payload.account_id,
            amount=payload.amount,
            description=payload.description,
            idempotency_key=idempotency_key
        )
        formatted = format_tx_response(tx)

        # 3. Update Idempotency status in the SAME transaction
        await IdempotencyService.record_success(
            db=db,
            idempotency_key=idempotency_key,
            response_code=status.HTTP_201_CREATED,
            response_body=formatted.model_dump(mode="json")
        )
        # ATOMIC COMMIT
        await db.commit()
        return formatted

    except HTTPException as he:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=he.status_code,
            error_detail=he.detail
        )
        raise he
    except Exception as e:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_detail="Internal transfer processing error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Withdrawal failed. Balance was not modified."
        ) from e


@router.post("/transfer", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def transfer_funds(
    payload: TransferRequest,
    idempotency_key: str = Depends(get_required_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Transfer funds between two accounts.
    Guarantees deadlock-free concurrency via deterministic lock ordering and double-entry equilibrium.
    """
    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors have read-only access and cannot initiate transfers."
        )

    # 1. Idempotency Check & Reserve
    request_path = "/api/v1/transactions/transfer"
    payload_hash = IdempotencyService.compute_hash(payload.model_dump())
    cached = await IdempotencyService.check_or_reserve(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=request_path,
        payload_hash=payload_hash
    )
    if cached:
        status_code, body = cached
        return JSONResponse(status_code=status_code, content=body)

    # 2. Execute Transfer
    try:
        tx = await TransferEngine.execute_transfer(
            db=db,
            actor=current_user,
            source_account_id=payload.source_account_id,
            destination_account_id=payload.destination_account_id,
            amount=payload.amount,
            description=payload.description,
            idempotency_key=idempotency_key
        )
        formatted = format_tx_response(tx)

        # 3. Update Idempotency status in the SAME transaction
        await IdempotencyService.record_success(
            db=db,
            idempotency_key=idempotency_key,
            response_code=status.HTTP_201_CREATED,
            response_body=formatted.model_dump(mode="json")
        )
        # ATOMIC COMMIT
        await db.commit()
        return formatted

    except HTTPException as he:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=he.status_code,
            error_detail=he.detail
        )
        raise he
    except Exception as e:
        await db.rollback()
        await IdempotencyService.record_failure_isolated(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=request_path,
            payload_hash=payload_hash,
            response_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_detail="Internal transfer processing error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer failed. Balances were not modified."
        ) from e


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full transaction details and double-entry lines."""
    stmt = (
        select(LedgerTransaction)
        .where(LedgerTransaction.id == transaction_id)
        .options(selectinload(LedgerTransaction.entries))
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    # Authorization: account holders may only view transactions affecting their accounts
    if current_user.role not in ["ADMIN", "AUDITOR"]:
        account_ids = [entry.account_id for entry in tx.entries]
        user_accounts_stmt = select(Account.id).where(
            Account.user_id == current_user.id,
            Account.id.in_(account_ids)
        )
        accessible = (await db.execute(user_accounts_stmt)).scalars().all()
        if not accessible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this transaction."
            )

    return format_tx_response(tx)


@router.get("", response_model=List[TransactionResponse])
async def list_transactions(
    account_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List transactions with optional account filtering and pagination."""
    if account_id:
        # Check ownership of specified account
        stmt_acc = select(Account).where(Account.id == account_id)
        acc = (await db.execute(stmt_acc)).scalar_one_or_none()
        if not acc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
        if current_user.role not in ["ADMIN", "AUDITOR"] and acc.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to account.")

        stmt = (
            select(LedgerTransaction)
            .join(LedgerEntry, LedgerEntry.transaction_id == LedgerTransaction.id)
            .where(LedgerEntry.account_id == account_id)
            .distinct()
            .options(selectinload(LedgerTransaction.entries))
            .order_by(LedgerTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    elif current_user.role in ["ADMIN", "AUDITOR"]:
        stmt = (
            select(LedgerTransaction)
            .options(selectinload(LedgerTransaction.entries))
            .order_by(LedgerTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    else:
        # User's own accounts
        user_acc_ids_stmt = select(Account.id).where(Account.user_id == current_user.id)
        user_acc_ids = (await db.execute(user_acc_ids_stmt)).scalars().all()
        if not user_acc_ids:
            return []

        stmt = (
            select(LedgerTransaction)
            .join(LedgerEntry, LedgerEntry.transaction_id == LedgerTransaction.id)
            .where(LedgerEntry.account_id.in_(user_acc_ids))
            .distinct()
            .options(selectinload(LedgerTransaction.entries))
            .order_by(LedgerTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

    result = await db.execute(stmt)
    txs = result.scalars().all()
    return [format_tx_response(tx) for tx in txs]
