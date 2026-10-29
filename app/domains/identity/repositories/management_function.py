from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.management_function import ManagementFunctionModel


class ManagementFunctionRepository:

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, function_id: str) -> ManagementFunctionModel | None:
        # Lấy một chức năng quản lý theo ID.
        return self.session.get(ManagementFunctionModel, function_id)

    def get_by_name(self, name: str) -> ManagementFunctionModel | None:
        # Lấy một chức năng quản lý theo tên duy nhất.
        return self.session.scalar(select(ManagementFunctionModel).where(ManagementFunctionModel.name == name))

    def get_all(self) -> list[ManagementFunctionModel]:
        # Lấy toàn bộ chức năng quản lý hiện có.
        return list(self.session.scalars(select(ManagementFunctionModel)))
