from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiCategoryMapping(Base):
    __tablename__ = "poi_category_mapping"

    poi_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("point_of_interest.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # A Category is master data. Deleting a Category must not silently
    # unclassify POIs; callers must remove mappings explicitly first.
    poi_category_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("poi_category.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
