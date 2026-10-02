from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OfflinePackage(Base):
    __tablename__ = "offline_package"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("poi_category.id", ondelete="RESTRICT"), nullable=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id", ondelete="RESTRICT"), nullable=False, index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("language.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    total_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
