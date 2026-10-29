from sqlalchemy import select
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

    def get_all(self) -> list[RoleModel]:
        # Lấy toàn bộ role theo thứ tự tên ổn định.
        statement = select(RoleModel).order_by(RoleModel.name)
        return list(self.session.scalars(statement))

    def add(self, role: RoleModel) -> None:
        # Đưa role mới vào Session; service chịu trách nhiệm commit.
        self.session.add(role)
