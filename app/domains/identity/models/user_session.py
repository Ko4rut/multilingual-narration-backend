from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSessionModel(Base):
    # Model đại diện cho một phiên đăng nhập của người dùng quản lý trong hệ thống.
    # Mỗi phiên đăng nhập được xác định bởi một ID duy nhất và liên kết với một người dùng quản lý cụ thể. 
    # Phiên đăng nhập có thể được tạo ra khi người dùng đăng nhập và có thể bị thu hồi khi người dùng đăng xuất hoặc khi phiên đăng nhập hết hạn
    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint(
            "expires_at > created_at",
            name="ck_user_session_expires_after_creation",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_user_session_revoked_after_creation",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("manager_user.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
