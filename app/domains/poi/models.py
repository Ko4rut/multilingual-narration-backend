from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiCategory(Base):
    __tablename__ = "poi_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_code: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )


class PointOfInterest(Base):
    __tablename__ = "point_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("region.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    poi_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_checksum_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    poi_qr_code: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    poi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    poi_location: Mapped[str] = mapped_column(String(500), nullable=False)
    poi_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    trigger_radius_meter: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    last_updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class PoiCategoryMapping(Base):
    __tablename__ = "poi_category_mapping"

    poi_id: Mapped[int] = mapped_column(
        ForeignKey("point_of_interest.id", ondelete="CASCADE"), primary_key=True
    )
    poi_category_id: Mapped[int] = mapped_column(
        ForeignKey("poi_category.id", ondelete="CASCADE"), primary_key=True
    )
