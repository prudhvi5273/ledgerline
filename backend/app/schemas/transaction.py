from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_financial_amount(v: Decimal) -> Decimal:
    """Validate that financial amounts are finite, positive, bounded, and have max 4 decimal places."""
    if not v.is_finite():
        raise ValueError("Financial amount must be a finite number (no NaN or Infinity)")
    if v <= Decimal("0.0000"):
        raise ValueError("Amount must be strictly greater than zero")
    if v > Decimal("1000000000.0000"):
        raise ValueError("Amount exceeds maximum single transaction limit of 1,000,000,000.0000")
    # Check decimal places
    exponent = v.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -4:
        raise ValueError("Amount cannot have more than 4 decimal places")
    return v


class DepositRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(..., description="Deposit amount must be strictly positive")
    description: Optional[str] = Field("External deposit", max_length=255)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: Decimal) -> Decimal:
        return validate_financial_amount(v)


class WithdrawRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(..., description="Withdrawal amount must be strictly positive")
    description: Optional[str] = Field("External withdrawal", max_length=255)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: Decimal) -> Decimal:
        return validate_financial_amount(v)


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal = Field(..., description="Transfer amount must be strictly positive")
    description: Optional[str] = Field("Account transfer", max_length=255)

    @field_validator("amount")
    @classmethod
    def check_amount(cls, v: Decimal) -> Decimal:
        return validate_financial_amount(v)

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
