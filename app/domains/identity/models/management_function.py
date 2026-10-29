from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ManagementFunctionModel(Base):
    # Model đại diện cho một chức năng quản lý trong hệ thống.
    # Mỗi chức năng quản lý có một tên duy nhất và được xác định bởi một ID duy nhất.
    __tablename__ = "management_function"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
