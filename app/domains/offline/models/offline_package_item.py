from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflinePackageItem(Base):
    __tablename__ = "offline_package_item"
    __table_args__ = (
        UniqueConstraint(
            "package_id",
            "poi_content_id",
            name="uq_offline_package_item_package_content",
        ),
        CheckConstraint(
            "content_version >= 1",
            name="ck_offline_package_item_content_version_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    package_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("offline_package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("point_of_interest.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    poi_content_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("poi_content.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    audio_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("content_audio.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
