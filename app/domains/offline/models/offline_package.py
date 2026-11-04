from __future__ import annotations

from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflinePackageStatus(str, PythonEnum):
    BUILDING = "BUILDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class OfflinePackage(Base):
    __tablename__ = "offline_package"
    __table_args__ = (
        UniqueConstraint("package_key", name="uq_offline_package_key"),
        CheckConstraint("package_version >= 1", name="ck_offline_package_version_positive"),
        CheckConstraint("schema_version >= 1", name="ck_offline_package_schema_version_positive"),
        CheckConstraint("total_size IS NULL OR total_size >= 0", name="ck_offline_package_total_size_nonnegative"),
        CheckConstraint(
            "published_at IS NULL OR published_at >= created_at",
            name="ck_offline_package_published_after_creation",
        ),
        Index("ix_offline_package_region_language", "region_id", "language_id"),
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
    package_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    total_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    package_checksum_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    package_status: Mapped[OfflinePackageStatus] = mapped_column(
        Enum(OfflinePackageStatus, name="offline_package_status", validate_strings=True),
        nullable=False,
        index=True,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
