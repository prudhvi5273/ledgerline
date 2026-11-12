from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction
from app.models.user import User
from app.services.audit_service import AuditService


class TransferEngine:
    @staticmethod
    def _generate_reference(prefix: str) -> str:
        """Generate high-entropy unique transaction reference."""
        return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

    @classmethod
    async def get_or_create_system_clearing_account(cls, db: AsyncSession) -> Account:
        """
        Ensure the internal settlement clearing account exists.
        Reads without lock so that the caller can acquire locks in strict deterministic ascending order.
        """
        clearing_id = uuid.UUID(settings.SYSTEM_CLEARING_ACCOUNT_ID)
        stmt = select(Account).where(Account.id == clearing_id)
        result = await db.execute(stmt)
        clearing_acc = result.scalar_one_or_none()

        if not clearing_acc:
            # Check if system user exists or find an admin
            stmt_user = select(User).where(User.role == "ADMIN")
            user_result = await db.execute(stmt_user)
            admin_user = user_result.scalars().first()

            if not admin_user:
                # Create a baseline system user for the clearing account
                admin_user = User(
                    email="system.clearing@ledgerline.internal",
                    password_hash="[LOCKED_SYSTEM_ACCOUNT]",
                    full_name="LedgerLine Clearing Authority",
                    role="ADMIN",
                    is_active=True
                )
                db.add(admin_user)
                await db.flush()

            clearing_acc = Account(
                id=clearing_id,
                user_id=admin_user.id,
                account_number="SYS-CLEARING-001",
                currency="INR",
                balance=Decimal("0.0000"),
                status="ACTIVE",
                account_type="SYSTEM_CLEARING"
            )
            db.add(clearing_acc)
            await db.flush()

        return clearing_acc

    @classmethod
    async def execute_transfer(
        cls,
        db: AsyncSession,
        actor: User,
        source_account_id: uuid.UUID,
        destination_account_id: uuid.UUID,
        amount: Decimal,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> LedgerTransaction:
        """
        Execute an internal account-to-account transfer with strict double-entry invariants,
        deterministic row locking, and non-negative balance enforcement.
        """
        if amount <= Decimal("0.0000"):
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason="INVALID_AMOUNT",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer amount must be strictly greater than zero."
            )

        if source_account_id == destination_account_id:
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason="IDENTICAL_ACCOUNTS",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination accounts must be distinct."
            )

        # 1. Deterministic lock order (sort IDs ascending to eliminate deadlocks)
        sorted_ids = sorted([source_account_id, destination_account_id], key=lambda x: str(x))

        stmt = (
            select(Account)
            .where(Account.id.in_(sorted_ids))
            .order_by(Account.id.asc())
            .with_for_update()
        )
        result = await db.execute(stmt)
        accounts_map: Dict[uuid.UUID, Account] = {acc.id: acc for acc in result.scalars().all()}

        # Verify both accounts exist
        if source_account_id not in accounts_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source account does not exist."
            )
        if destination_account_id not in accounts_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination account does not exist."
            )

        source_acc = accounts_map[source_account_id]
        dest_acc = accounts_map[destination_account_id]

        # 2. Ownership verification: caller must own source account unless ADMIN
        if actor.role != "ADMIN" and source_acc.user_id != actor.id:
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason="UNAUTHORIZED_ACCOUNT_ACCESS",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to transfer funds from this account."
            )

        # 3. Status checks
        if source_acc.status != "ACTIVE":
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason=f"SOURCE_ACCOUNT_{source_acc.status}",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source account is {source_acc.status.lower()} and cannot send funds."
            )

        if dest_acc.status != "ACTIVE":
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason=f"DESTINATION_ACCOUNT_{dest_acc.status}",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination account is {dest_acc.status.lower()} and cannot receive funds."
            )

        # 4. Currency matching
        if source_acc.currency != dest_acc.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross-currency transfers are not supported. Accounts must share identical currency."
            )

        # 5. Non-negative balance check under exclusive lock
        if source_acc.balance < amount:
            await AuditService.log_refusal_isolated(
                event_type="TRANSFER_REFUSED",
                refusal_reason="INSUFFICIENT_FUNDS",
                actor_id=actor.id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                idempotency_key=idempotency_key,
                metadata_info={
                    "available_balance": str(source_acc.balance),
                    "requested_amount": str(amount)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds in source account."
            )

        # 6. Apply balance mutations inside lock
        source_acc.balance -= amount
        dest_acc.balance += amount

        # 7. Create Journal Header
        ref_id = cls._generate_reference("TX-TRF")
        tx_header = LedgerTransaction(
            reference_id=ref_id,
            transaction_type="TRANSFER",
            status="POSTED",
            description=description or f"Transfer from {source_acc.account_number} to {dest_acc.account_number}",
            total_amount=amount,
            currency=source_acc.currency
        )
        db.add(tx_header)
        await db.flush()

        # 8. Create Double-Entry Pair: 1 Debit (Source), 1 Credit (Destination)
        debit_entry = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=source_acc.id,
            entry_type="DEBIT",
            amount=amount,
            balance_after=source_acc.balance
        )
        credit_entry = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=dest_acc.id,
            entry_type="CREDIT",
            amount=amount,
            balance_after=dest_acc.balance
        )
        db.add(debit_entry)
        db.add(credit_entry)
        tx_header.entries = [debit_entry, credit_entry]
        await db.flush()

        # 9. Audit Log
        await AuditService.log_event(
            db=db,
            actor_id=actor.id,
            event_type="TRANSFER_SUCCESS",
            status="SUCCESS",
            source_account_id=source_acc.id,
            destination_account_id=dest_acc.id,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata_info={"reference_id": ref_id}
        )

        return tx_header

    @classmethod
    async def execute_deposit(
        cls,
        db: AsyncSession,
        actor: User,
        account_id: uuid.UUID,
        amount: Decimal,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> LedgerTransaction:
        """
        Execute an external deposit.
        Credits user account and debits the SYSTEM_CLEARING account to preserve double-entry integrity.
        """
        if amount <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deposit amount must be strictly positive."
            )

        clearing_acc = await cls.get_or_create_system_clearing_account(db)

        # Deterministic lock order
        sorted_ids = sorted([account_id, clearing_acc.id], key=lambda x: str(x))
        stmt = select(Account).where(Account.id.in_(sorted_ids)).order_by(Account.id.asc()).with_for_update()
        result = await db.execute(stmt)
        accounts_map = {acc.id: acc for acc in result.scalars().all()}

        user_acc = accounts_map.get(account_id)
        if not user_acc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

        # Ownership verification
        if actor.role != "ADMIN" and user_acc.user_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to deposit to this account.")

        if user_acc.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Account is {user_acc.status.lower()}.")

        # Mutate balances
        clearing_acc.balance -= amount
        user_acc.balance += amount

        # Create Journal Header
        ref_id = cls._generate_reference("TX-DEP")
        tx_header = LedgerTransaction(
            reference_id=ref_id,
            transaction_type="DEPOSIT",
            status="POSTED",
            description=description or f"External deposit into {user_acc.account_number}",
            total_amount=amount,
            currency=user_acc.currency
        )
        db.add(tx_header)
        await db.flush()

        # Balanced double-entry pair: DEBIT clearing account, CREDIT user account
        debit_clearing = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=clearing_acc.id,
            entry_type="DEBIT",
            amount=amount,
            balance_after=clearing_acc.balance
        )
        credit_user = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=user_acc.id,
            entry_type="CREDIT",
            amount=amount,
            balance_after=user_acc.balance
        )
        db.add(debit_clearing)
        db.add(credit_user)
        tx_header.entries = [debit_clearing, credit_user]
        await db.flush()

        await AuditService.log_event(
            db=db,
            actor_id=actor.id,
            event_type="DEPOSIT_SUCCESS",
            status="SUCCESS",
            source_account_id=clearing_acc.id,
            destination_account_id=user_acc.id,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata_info={"reference_id": ref_id}
        )

        return tx_header

    @classmethod
    async def execute_withdrawal(
        cls,
        db: AsyncSession,
        actor: User,
        account_id: uuid.UUID,
        amount: Decimal,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> LedgerTransaction:
        """
        Execute an external withdrawal.
        Debits user account and credits the SYSTEM_CLEARING account to preserve double-entry balance.
        """
        if amount <= Decimal("0.0000"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Withdrawal amount must be strictly positive."
            )

        clearing_acc = await cls.get_or_create_system_clearing_account(db)

        # Deterministic lock order
        sorted_ids = sorted([account_id, clearing_acc.id], key=lambda x: str(x))
        stmt = select(Account).where(Account.id.in_(sorted_ids)).order_by(Account.id.asc()).with_for_update()
        result = await db.execute(stmt)
        accounts_map = {acc.id: acc for acc in result.scalars().all()}

        user_acc = accounts_map.get(account_id)
        if not user_acc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

        # Ownership verification
        if actor.role != "ADMIN" and user_acc.user_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to withdraw from this account.")

        if user_acc.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Account is {user_acc.status.lower()}.")

        # Balance verification inside locked transaction
        if user_acc.balance < amount:
            await AuditService.log_refusal_isolated(
                event_type="WITHDRAWAL_REFUSED",
                refusal_reason="INSUFFICIENT_FUNDS",
                actor_id=actor.id,
                source_account_id=user_acc.id,
                destination_account_id=clearing_acc.id,
                amount=amount,
                idempotency_key=idempotency_key
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds for withdrawal."
            )

        # Mutate balances
        user_acc.balance -= amount
        clearing_acc.balance += amount

        # Create Journal Header
        ref_id = cls._generate_reference("TX-WTH")
        tx_header = LedgerTransaction(
            reference_id=ref_id,
            transaction_type="WITHDRAWAL",
            status="POSTED",
            description=description or f"External withdrawal from {user_acc.account_number}",
            total_amount=amount,
            currency=user_acc.currency
        )
        db.add(tx_header)
        await db.flush()

        # Balanced double-entry pair: DEBIT user account, CREDIT clearing account
        debit_user = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=user_acc.id,
            entry_type="DEBIT",
            amount=amount,
            balance_after=user_acc.balance
        )
        credit_clearing = LedgerEntry(
            transaction_id=tx_header.id,
            account_id=clearing_acc.id,
            entry_type="CREDIT",
            amount=amount,
            balance_after=clearing_acc.balance
        )
        db.add(debit_user)
        db.add(credit_clearing)
        tx_header.entries = [debit_user, credit_clearing]
        await db.flush()

        await AuditService.log_event(
            db=db,
            actor_id=actor.id,
            event_type="WITHDRAWAL_SUCCESS",
            status="SUCCESS",
            source_account_id=user_acc.id,
            destination_account_id=clearing_acc.id,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata_info={"reference_id": ref_id}
        )

        return tx_header
