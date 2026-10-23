from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Language(Base):
    __tablename__ = "language"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    language_code: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=True
    )
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    language_status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
