from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ManagerUserStatus(str, Enum):
    # Trạng thái của người dùng quản lý trong hệ thống.
    # Người dùng quản lý có thể ở trạng thái "ACTIVE" (hoạt động) hoặc "INACTIVE" (không hoạt động). 
    # Trạng thái này được sử dụng để xác định xem người dùng quản lý có thể đăng nhập và sử dụng hệ thống hay không
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ManagerUserModel(Base):
    # Model đại diện cho một người dùng quản lý trong hệ thống.
    # Mỗi người dùng quản lý có một email duy nhất và được xác định bởi một ID duy nhất.
    __tablename__ = "manager_user"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(50), ForeignKey("role.id", ondelete="RESTRICT"), nullable=False, index=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
