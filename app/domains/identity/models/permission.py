from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = (
        UniqueConstraint(
            "function_id",
            "action_id",
            name="uq_permission_function_action",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    function_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("management_function.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("action.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
