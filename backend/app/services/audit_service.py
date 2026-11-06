import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        status: str,
        actor_id: Optional[uuid.UUID] = None,
        refusal_reason: Optional[str] = None,
        source_account_id: Optional[uuid.UUID] = None,
        destination_account_id: Optional[uuid.UUID] = None,
        amount: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None,
        metadata_info: Optional[dict] = None
    ) -> AuditLog:
        """Record an audit event within the active session."""
        audit_entry = AuditLog(
            actor_id=actor_id,
            event_type=event_type,
            status=status,
            refusal_reason=refusal_reason,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata_info=metadata_info or {}
        )
        db.add(audit_entry)
        await db.flush()
        return audit_entry

    @staticmethod
    async def log_refusal_isolated(
        event_type: str,
        refusal_reason: str,
        actor_id: Optional[uuid.UUID] = None,
        source_account_id: Optional[uuid.UUID] = None,
        destination_account_id: Optional[uuid.UUID] = None,
        amount: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None,
        metadata_info: Optional[dict] = None
    ) -> None:
        """
        Record a refused attempt in an isolated database transaction
        so the log persists even if the main transaction is aborted or rolled back.
        """
        async with AsyncSessionLocal() as session:
            try:
                audit_entry = AuditLog(
                    actor_id=actor_id,
                    event_type=event_type,
                    status="REFUSED",
                    refusal_reason=refusal_reason,
                    source_account_id=source_account_id,
                    destination_account_id=destination_account_id,
                    amount=amount,
                    idempotency_key=idempotency_key,
                    metadata_info=metadata_info or {}
                )
                session.add(audit_entry)
                await session.commit()
            except Exception:
                await session.rollback()
