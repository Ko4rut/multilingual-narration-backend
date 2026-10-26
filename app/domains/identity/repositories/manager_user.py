from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.manager_user import ManagerUserModel


class ManagerUserRepository:
    """Persistence operations used by manager-user use cases."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> ManagerUserModel | None:
        return self.session.get(ManagerUserModel, user_id)

    def get_by_email(self, email: str) -> ManagerUserModel | None:
        statement = select(ManagerUserModel).where(ManagerUserModel.email == email)
        return self.session.scalar(statement)

    def list(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[ManagerUserModel]:
        statement = (
            select(ManagerUserModel)
            .order_by(ManagerUserModel.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add(self, manager_user: ManagerUserModel) -> None:
        self.session.add(manager_user)
