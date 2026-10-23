from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Region(Base):
    __tablename__ = "region"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_name: Mapped[str] = mapped_column(String(150), nullable=False)
    region_code: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
