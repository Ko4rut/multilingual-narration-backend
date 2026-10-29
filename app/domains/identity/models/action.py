from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActionModel(Base):
    # Model đại diện cho một hành động trong hệ thống. 
    # Mỗi hành động có một tên duy nhất và được xác định bởi một ID duy nhất.
    __tablename__ = "action"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
