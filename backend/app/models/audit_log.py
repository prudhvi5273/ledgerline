import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True  # TRANSFER_SUCCESS, TRANSFER_REFUSED, DEPOSIT_SUCCESS, etc.
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False  # SUCCESS | REFUSED | ERROR
    )
    refusal_reason: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    source_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    destination_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True
    )
    metadata_info: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCESS', 'REFUSED', 'ERROR')",
            name="chk_audit_status_valid"
        ),
        Index("idx_audit_created_event", "created_at", "event_type"),
    )

    # Relationships
    actor = relationship("User", back_populates="audit_logs")
