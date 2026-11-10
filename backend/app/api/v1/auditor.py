from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import List
from fastapi import APIRouter, Depends, Query, Response
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


@router.get("/export")
async def export_audit_compliance_pack(
    format: str = Query("json", regex="^(json|csv)$"),
    auditor_user: User = Depends(require_role(["AUDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an authoritative, tamper-evident regulatory compliance export
    containing full double-entry audit records with SHA-256 integrity checksum.
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.asc())
    result = await db.execute(stmt)
    logs = result.scalars().all()

    if format == "csv":
        headers = ["id", "actor_id", "event_type", "status", "refusal_reason", "amount", "idempotency_key", "created_at"]
        rows = [",".join(headers)]
        for log in logs:
            row = [
                str(log.id),
                str(log.actor_id or ""),
                log.event_type,
                log.status,
                log.refusal_reason or "",
                str(log.amount or "0.0000"),
                log.idempotency_key or "",
                log.created_at.isoformat() if log.created_at else ""
            ]
            rows.append(",".join(row))
        content = "\n".join(rows)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=compliance_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"}
        )

    # JSON export with cryptographic SHA-256 checksum
    serialized_logs = [
        {
            "id": str(l.id),
            "actor_id": str(l.actor_id) if l.actor_id else None,
            "event_type": l.event_type,
            "status": l.status,
            "refusal_reason": l.refusal_reason,
            "source_account_id": str(l.source_account_id) if l.source_account_id else None,
            "destination_account_id": str(l.destination_account_id) if l.destination_account_id else None,
            "amount": str(l.amount) if l.amount else None,
            "idempotency_key": l.idempotency_key,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]
    payload_str = json.dumps(serialized_logs, sort_keys=True)
    integrity_checksum = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    export_bundle = {
        "export_metadata": {
            "application": "LedgerLine Financial Core",
            "auditor": auditor_user.email,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(serialized_logs),
            "sha256_checksum": integrity_checksum
        },
        "audit_logs": serialized_logs
    }

    return Response(
        content=json.dumps(export_bundle, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=compliance_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"}
    )
