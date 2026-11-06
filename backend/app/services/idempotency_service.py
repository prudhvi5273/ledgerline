import hashlib
import json
from typing import Any, Dict, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.idempotency import IdempotencyRecord


class IdempotencyService:
    @staticmethod
    def compute_hash(payload: Any) -> str:
        """Compute deterministic SHA-256 hash of the request payload."""
        if isinstance(payload, dict):
            # Sort keys to ensure deterministic serialization
            serialized = json.dumps(payload, sort_keys=True, default=str)
        else:
            serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    async def check_or_reserve(
        db: AsyncSession,
        idempotency_key: str,
        user_id: uuid.UUID,
        request_path: str,
        payload_hash: str
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Check if idempotency key exists.
        - If completed: returns cached (status_code, body).
        - If in-flight ('PENDING'): raises 409 Conflict.
        - If payload hash mismatch: raises 409 Conflict.
        - If new: creates PENDING record. Handles concurrent race condition gracefully.
        """
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key
        ).with_for_update()
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            # Check payload integrity
            if record.request_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key was previously used with a different request payload."
                )

            # Check execution state
            if record.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A transaction with this Idempotency-Key is currently processing. Please retry shortly."
                )
            
            # Replay cached result
            if record.status == "COMPLETED":
                return (record.response_code or 200, record.response_body or {})
            
            # If previously recorded as failed
            raise HTTPException(
                status_code=record.response_code or status.HTTP_400_BAD_REQUEST,
                detail=record.response_body.get("detail", "Previous transaction failed") if record.response_body else "Transaction failed"
            )

        # Attempt to insert new PENDING record
        try:
            new_record = IdempotencyRecord(
                idempotency_key=idempotency_key,
                user_id=user_id,
                request_path=request_path,
                request_hash=payload_hash,
                status="PENDING"
            )
            db.add(new_record)
            await db.flush()
            return None
        except IntegrityError:
            # Race condition: Another concurrent worker just committed or inserted this key
            await db.rollback()
            # Re-query
            res_retry = await db.execute(
                select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
            )
            r_rec = res_retry.scalar_one_or_none()
            if r_rec and r_rec.status == "COMPLETED":
                return (r_rec.response_code or 200, r_rec.response_body or {})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A concurrent transaction with this Idempotency-Key is currently processing."
            )

    @staticmethod
    async def record_success(
        db: AsyncSession,
        idempotency_key: str,
        response_code: int,
        response_body: Dict[str, Any]
    ) -> None:
        """Mark idempotency record as COMPLETED with cached response."""
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key
        ).with_for_update()
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            record.status = "COMPLETED"
            record.response_code = response_code
            record.response_body = response_body
            await db.flush()

    @staticmethod
    async def record_failure_isolated(
        idempotency_key: str,
        user_id: uuid.UUID,
        request_path: str,
        payload_hash: str,
        response_code: int,
        error_detail: str
    ) -> None:
        """
        Record failure in an isolated database session so that failure status
        persists even after the main financial transaction rolls back.
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(IdempotencyRecord).where(
                    IdempotencyRecord.idempotency_key == idempotency_key
                ).with_for_update()
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if record:
                    record.status = "FAILED"
                    record.response_code = response_code
                    record.response_body = {"detail": error_detail}
                else:
                    new_rec = IdempotencyRecord(
                        idempotency_key=idempotency_key,
                        user_id=user_id,
                        request_path=request_path,
                        request_hash=payload_hash,
                        status="FAILED",
                        response_code=response_code,
                        response_body={"detail": error_detail}
                    )
                    session.add(new_rec)
                await session.commit()
            except Exception:
                await session.rollback()
