import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    request_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",  # PENDING | COMPLETED | FAILED
        nullable=False
    )
    response_code: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )
    response_body: Mapped[dict] = mapped_column(
        JSON,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="chk_idemp_status_valid"
        ),
        Index("idx_idemp_user_created", "user_id", "created_at"),
    )

    # Relationships
    user = relationship("User")
