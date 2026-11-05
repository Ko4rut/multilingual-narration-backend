from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
        CheckConstraint("content_version >= 1", name="ck_poi_content_version"),
        CheckConstraint(
            "upper(content_status) IN ('DRAFT', 'WAITING_APPROVAL', 'REJECTED', 'APPROVED', 'PUBLISHED', 'ARCHIVED')",
            name="ck_poi_content_status",
        ),
        CheckConstraint("approved_at IS NULL OR approved_at >= created_at", name="ck_poi_content_approved_at"),
        CheckConstraint(
            "published_at IS NULL OR approved_at IS NULL OR published_at >= approved_at",
            name="ck_poi_content_published_at",
        ),
        Index("ix_poi_content_distribution", "poi_id", "language_id", "content_status"),
        Index(
            "uq_poi_content_published_language", "poi_id", "language_id", unique=True,
            postgresql_where=text("upper(content_status) = 'PUBLISHED'"),
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
