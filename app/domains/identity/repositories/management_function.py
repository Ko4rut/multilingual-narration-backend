from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.management_function import ManagementFunctionModel


class ManagementFunctionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, function_id: str) -> ManagementFunctionModel | None:
        return self.session.get(ManagementFunctionModel, function_id)

    def get_by_name(self, name: str) -> ManagementFunctionModel | None:
        statement = select(ManagementFunctionModel).where(
            ManagementFunctionModel.name == name
        )
        return self.session.scalar(statement)

    def list_all(self) -> list[ManagementFunctionModel]:
        statement = select(ManagementFunctionModel).order_by(
            ManagementFunctionModel.name
        )
        return list(self.session.scalars(statement))
