from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningHistory(Base):
    __tablename__ = "listening_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="RESTRICT"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
