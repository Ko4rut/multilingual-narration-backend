from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domains.identity.models.role import RoleModel


class RoleRepository:

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, role_id: str) -> RoleModel | None:
        # Lấy role theo ID.
        return self.session.get(RoleModel, role_id)

    def get_by_name(self, name: str) -> RoleModel | None:
        # Lấy role theo tên duy nhất.
        statement = select(RoleModel).where(RoleModel.name == name)
        return self.session.scalar(statement)

    def get_all(self, *, search: str | None = None) -> list[RoleModel]:
        """Lấy role theo từ khóa và thứ tự tên ổn định."""

        statement = select(RoleModel)
        if search is not None:
            # Escape wildcard để từ khóa được hiểu là văn bản cần tìm kiếm.
            escaped_search = (
                search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped_search}%"
            statement = statement.where(
                or_(
                    RoleModel.id.ilike(pattern, escape="\\"),
                    RoleModel.name.ilike(pattern, escape="\\"),
                    RoleModel.description.ilike(pattern, escape="\\"),
                )
            )
        statement = statement.order_by(RoleModel.name, RoleModel.id)
        return list(self.session.scalars(statement))

    def add(self, role: RoleModel) -> None:
        # Đưa role mới vào Session; service chịu trách nhiệm commit.
        self.session.add(role)
