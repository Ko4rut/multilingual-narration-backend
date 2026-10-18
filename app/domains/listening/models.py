from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    poi_content_id: Mapped[int] = mapped_column(
        ForeignKey("poi_content.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[int] = mapped_column(
        ForeignKey("point_of_interest.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
