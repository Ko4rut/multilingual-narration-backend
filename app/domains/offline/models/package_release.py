"""Immutable release index: only committed releases can be fetched by Mobile."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflinePackageRelease(Base):
    __tablename__ = "offline_package_release"
    __table_args__ = (
        CheckConstraint("package_version >= 1", name="ck_offline_release_version"),
    )

    package_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("offline_package.id", ondelete="CASCADE"),
        primary_key=True,
    )
    package_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    manifest_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
