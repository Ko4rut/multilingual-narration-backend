"""Durable requests to reconcile published offline packages after source commits."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflineBuildRequest(Base):
    __tablename__ = "offline_build_request"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_offline_build_attempts"),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED')",
            name="ck_offline_build_status",
        ),
        Index("ix_offline_build_due", "status", "next_attempt_at"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    # Keep the old region ID even when a POI moves to another region.
    region_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # NULL means inspect all SUPPORTED languages in this region.
    language_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
