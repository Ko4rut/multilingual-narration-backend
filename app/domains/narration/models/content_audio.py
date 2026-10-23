from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentAudio(Base):
    __tablename__ = "content_audio"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    poi_content_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("poi_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audio_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    audio_size: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    audio_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    audio_checksum_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
