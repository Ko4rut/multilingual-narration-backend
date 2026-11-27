"""Shared POI classification vocabulary consumed by POI and Offline domains."""

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiCategory(Base):
    __tablename__ = "poi_category"
    __table_args__ = (
        UniqueConstraint("category_name", name="uq_poi_category_name"),
        CheckConstraint(
            "category_name = btrim(category_name) AND category_name <> ''",
            name="ck_poi_category_name_nonempty_trimmed",
        ),
        # Legacy seeded categories use uppercase codes. New API accepts only
        # lowercase codes; do not rewrite existing referenced codes silently.
        CheckConstraint(
            "category_code ~ '^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$'",
            name="ck_poi_category_code_format",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
