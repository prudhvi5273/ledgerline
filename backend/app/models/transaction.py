import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    reference_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True  # TRANSFER | DEPOSIT | WITHDRAWAL | REVERSAL
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="POSTED",
        nullable=False  # POSTED | REVERSED
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    __table_args__ = (
        CheckConstraint(
            "total_amount > 0",
            name="chk_ledger_tx_amount_positive"
        ),
        CheckConstraint(
            "transaction_type IN ('TRANSFER', 'DEPOSIT', 'WITHDRAWAL', 'REVERSAL')",
            name="chk_ledger_tx_type_valid"
        ),
    )

    # Relationships
    entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin")


# Application-level immutability guard
from sqlalchemy import event

@event.listens_for(LedgerTransaction, "before_update")
@event.listens_for(LedgerTransaction, "before_delete")
def enforce_ledger_transaction_immutability(mapper, connection, target):
    raise PermissionError("Ledger transactions are strictly immutable. UPDATE and DELETE operations are forbidden.")
