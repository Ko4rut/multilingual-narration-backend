from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RolePermissionModel(Base):
    __tablename__ = "role_permission"

    permission_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("permission.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
