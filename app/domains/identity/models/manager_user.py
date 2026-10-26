from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.identity.enums import ManagerUserStatus


class ManagerUserModel(Base):
    __tablename__ = "manager_user"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    role_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("role.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    user_status: Mapped[ManagerUserStatus] = mapped_column(
        SqlEnum(
            ManagerUserStatus,
            name="manager_user_status",
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
