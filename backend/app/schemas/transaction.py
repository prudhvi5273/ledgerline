from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DepositRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Deposit amount must be strictly positive")
    description: Optional[str] = Field("External deposit", max_length=255)


class WithdrawRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Withdrawal amount must be strictly positive")
    description: Optional[str] = Field("External withdrawal", max_length=255)


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Transfer amount must be strictly positive")
    description: Optional[str] = Field("Account transfer", max_length=255)

    @model_validator(mode="after")
    def validate_different_accounts(self) -> "TransferRequest":
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination accounts must be distinct")
        return self


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    entry_type: str  # DEBIT | CREDIT
    amount: Decimal
    balance_after: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    reference_id: str
    transaction_type: str
    status: str
    description: Optional[str]
    total_amount: Decimal
    currency: str
    created_at: datetime
    entries: List[LedgerEntryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StatementItem(BaseModel):
    entry_id: uuid.UUID
    transaction_id: uuid.UUID
    reference_id: str
    transaction_type: str
    entry_type: str  # DEBIT | CREDIT
    amount: Decimal
    balance_after: Decimal
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatementResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    currency: str
    current_balance: Decimal
    total_debits: Decimal
    total_credits: Decimal
    total_transactions: int
    items: List[StatementItem]
