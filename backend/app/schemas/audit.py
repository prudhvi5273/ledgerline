from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    event_type: str
    status: str
    refusal_reason: Optional[str]
    source_account_id: Optional[uuid.UUID]
    destination_account_id: Optional[uuid.UUID]
    amount: Optional[Decimal]
    idempotency_key: Optional[str]
    metadata_info: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationReport(BaseModel):
    total_accounts: int
    total_user_balance: Decimal
    system_clearing_balance: Decimal
    total_system_balance: Decimal
    total_ledger_debits: Decimal
    total_ledger_credits: Decimal
    is_balanced: bool
    discrepancy: Decimal
    checked_at: datetime
