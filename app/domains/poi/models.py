from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiCategory(Base):
    __tablename__ = "poi_category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

class PointOfInterest(Base):
    __tablename__ = "point_of_interest"
    __table_args__ = (Index("ix_point_of_interest_qr_code", "qr_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id", ondelete="RESTRICT"), nullable=False, index=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    qr_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    poi_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    poi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    trigger_radius: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    poi_location: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class PoiCategoryMapping(Base):
    __tablename__ = "poi_category_mapping"
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="CASCADE"), primary_key=True)
    poi_category_id: Mapped[int] = mapped_column(ForeignKey("poi_category.id", ondelete="CASCADE"), primary_key=True)
