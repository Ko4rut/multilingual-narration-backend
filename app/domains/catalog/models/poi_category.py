from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PoiCategory(Base):
    __tablename__ = "poi_category"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_code: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
