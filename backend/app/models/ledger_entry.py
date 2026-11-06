import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ledger_transactions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    entry_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False  # DEBIT | CREDIT
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="chk_ledger_entries_amount_positive"
        ),
        CheckConstraint(
            "entry_type IN ('DEBIT', 'CREDIT')",
            name="chk_ledger_entries_type_valid"
        ),
        Index("idx_ledger_entries_account_created", "account_id", "created_at"),
    )

    # Relationships
    transaction = relationship("LedgerTransaction", back_populates="entries")
    account = relationship("Account", back_populates="ledger_entries")


# Application-level immutability guard
@event.listens_for(LedgerEntry, "before_update")
@event.listens_for(LedgerEntry, "before_delete")
def enforce_ledger_entry_immutability(mapper, connection, target):
    raise PermissionError("Financial ledger entries are strictly immutable. UPDATE and DELETE operations are forbidden.")
