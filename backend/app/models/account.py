import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    account_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",  # ACTIVE | FROZEN | CLOSED
        nullable=False,
        index=True
    )
    account_type: Mapped[str] = mapped_column(
        String(30),
        default="USER_CHECKING",  # USER_CHECKING | USER_SAVINGS | SYSTEM_CLEARING
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "account_type = 'SYSTEM_CLEARING' OR balance >= 0",
            name="chk_accounts_balance_positive"
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'FROZEN', 'CLOSED')",
            name="chk_accounts_status_valid"
        ),
        Index("idx_accounts_user_currency", "user_id", "currency"),
    )

    # Relationships
    user = relationship("User", back_populates="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account")
