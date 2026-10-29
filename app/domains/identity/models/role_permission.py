from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RolePermissionModel(Base):
    # Model đại diện cho mối quan hệ giữa vai trò và quyền trong hệ thống.
    # Mỗi mối quan hệ được xác định bởi một cặp khóa chính gồm ``permission_id`` và ``role_id``.
    __tablename__ = "role_permission"

    permission_id: Mapped[str] = mapped_column(String(50), ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(50), ForeignKey("role.id", ondelete="CASCADE"), primary_key=True, index=True)
