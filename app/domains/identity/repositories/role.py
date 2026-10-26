from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.role import RoleModel


class RoleRepository:
    """Persistence operations used by role-related identity use cases."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, role_id: str) -> RoleModel | None:
        return self.session.get(RoleModel, role_id)

    def get_by_name(self, name: str) -> RoleModel | None:
        statement = select(RoleModel).where(RoleModel.name == name)
        return self.session.scalar(statement)

    def list_all(self) -> list[RoleModel]:
        statement = select(RoleModel).order_by(RoleModel.name)
        return list(self.session.scalars(statement))

    def add(self, role: RoleModel) -> None:
        self.session.add(role)
