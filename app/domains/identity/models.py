from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Action(Base):
    __tablename__ = "action"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

class ManagementFunction(Base):
    __tablename__ = "management_function"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

class Permission(Base):
    __tablename__ = "permission"
    id: Mapped[int] = mapped_column(primary_key=True)
    function_id: Mapped[int] = mapped_column(ForeignKey("management_function.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("action.id", ondelete="RESTRICT"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("function_id", "action_id", name="uq_permission_function_action"),)

class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

class RolePermission(Base):
    __tablename__ = "role_permission"
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)

class ManagementUser(Base):
    __tablename__ = "management_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id", ondelete="RESTRICT"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
