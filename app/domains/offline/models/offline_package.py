from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflinePackage(Base):
    __tablename__ = "offline_package"
    __table_args__ = (
        UniqueConstraint(
            "package_key",
            "package_version",
            name="uq_offline_package_key_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("poi_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    region_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("region.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("language.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    package_key: Mapped[str] = mapped_column(String(100), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    package_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    total_size: Mapped[int] = mapped_column(Integer, nullable=False)
    package_checksum_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    package_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
