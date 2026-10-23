from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    installation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    poi_content_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("poi_content.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[str] = mapped_column(
        String(50),
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
