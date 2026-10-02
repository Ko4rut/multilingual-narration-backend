from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiContent(Base):
    __tablename__ = "poi_content"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="CASCADE"), nullable=False, index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("language.id", ondelete="RESTRICT"), nullable=False, index=True)
    narration_title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration_script: Mapped[str] = mapped_column(Text, nullable=False)
    content_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("poi_id", "language_id", name="uq_poi_content_poi_language"),)

class ContentAudio(Base):
    __tablename__ = "content_audio"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_content_id: Mapped[int] = mapped_column(ForeignKey("poi_content.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    audio_size: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    checksum_sha25: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
