from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PermissionModel(Base):
    # Model đại diện cho một quyền trong hệ thống.
    # Mỗi quyền được xác định bởi một ID duy nhất và liên kết với một chức năng quản lý và một hành động cụ thể.
    __tablename__ = "permission"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    function_id: Mapped[str] = mapped_column(String(50), ForeignKey("management_function.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(50), ForeignKey("action.id", ondelete="RESTRICT"), nullable=False, index=True)
