from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiContent(Base):
    __tablename__ = "poi_content"
    __table_args__ = (
        UniqueConstraint(
            "poi_id",
            "language_id",
            "content_version",
            name="uq_poi_content_poi_language_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    poi_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("point_of_interest.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("language.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    narration_title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration_script: Mapped[str] = mapped_column(Text, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    published_by: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
