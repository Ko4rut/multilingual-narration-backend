from enum import Enum as PythonEnum

from sqlalchemy import CheckConstraint, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LanguageStatus(str, PythonEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class Language(Base):
    __tablename__ = "language"
    __table_args__ = (
        CheckConstraint(
            "language_code ~ '^[a-z]{2,3}$'",
            name="ck_language_code_format",
        ),
        CheckConstraint(
            "language_name = btrim(language_name) AND language_name <> ''",
            name="ck_language_name_nonempty_trimmed",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    language_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    language_status: Mapped[LanguageStatus] = mapped_column(
        Enum(
            LanguageStatus,
            name="language_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        index=True,
    )
