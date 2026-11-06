from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    currency: str = Field("INR", min_length=3, max_length=3, description="ISO 4217 Currency Code")
    account_type: str = Field("USER_CHECKING", pattern="^(USER_CHECKING|USER_SAVINGS)$")


class AccountStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|FROZEN|CLOSED)$")


class AccountResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_number: str
    currency: str
    balance: Decimal
    status: str
    account_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    currency: str
    balance: Decimal
    status: str
    as_of: datetime

    model_config = ConfigDict(from_attributes=True)
