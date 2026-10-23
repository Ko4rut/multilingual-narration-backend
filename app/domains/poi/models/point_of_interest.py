from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PointOfInterest(Base):
    __tablename__ = "point_of_interest"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("region.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    created_by: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    last_updated_by: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("manager_user.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
