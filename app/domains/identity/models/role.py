from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RoleModel(Base):
    # Model đại diện cho một vai trò trong hệ thống.
    # Mỗi vai trò có một tên duy nhất và được xác định bởi một ID duy nhất. 
    # Vai trò có thể được tạo ra và cập nhật bởi người dùng quản lý, và có thể được liên kết với nhiều quyền thông qua mối quan hệ nhiều-nhiều với bảng `role_permission`
    __tablename__ = "role"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("manager_user.id"))
    last_updated_by: Mapped[str | None] = mapped_column(ForeignKey("manager_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
