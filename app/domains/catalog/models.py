from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

class Language(Base):
    __tablename__ = "language"
    id: Mapped[int] = mapped_column(primary_key=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
