from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentAudio(Base):
    __tablename__ = "content_audio"
    __table_args__ = (
        UniqueConstraint("poi_content_id", name="uq_content_audio_content"),
        CheckConstraint("audio_size >= 0", name="ck_content_audio_size"),
        CheckConstraint("audio_duration_sec >= 0", name="ck_content_audio_duration"),
        CheckConstraint(
            "audio_source_type IN ('RECORD', 'TTS')",
            name="ck_content_audio_source",
        ),
        CheckConstraint(
            "audio_mime_type IN ('audio/mpeg', 'audio/aac', 'audio/ogg', "
            "'audio/wav', 'audio/mp4', 'audio/webm')",
            name="ck_content_audio_mime",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    poi_content_id: Mapped[str] = mapped_column(String(50),ForeignKey("poi_content.id", ondelete="CASCADE"),nullable=False,index=True,)
    audio_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    audio_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    audio_source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    audio_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    audio_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
