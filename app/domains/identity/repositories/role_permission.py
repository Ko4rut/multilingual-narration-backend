from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.identity.models.role_permission import RolePermissionModel


class RolePermissionRepository:
    def __init__(self, session: Session):
        self.session = session

    def exists(self, role_id: str, permission_id: str) -> bool:
        statement = select(RolePermissionModel.role_id).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.permission_id == permission_id,
        )
        return self.session.scalar(statement) is not None

    def list_by_role_id(self, role_id: str) -> list[RolePermissionModel]:
        statement = (
            select(RolePermissionModel)
            .where(RolePermissionModel.role_id == role_id)
            .order_by(RolePermissionModel.permission_id)
        )
        return list(self.session.scalars(statement))

    def add(self, role_permission: RolePermissionModel) -> None:
        self.session.add(role_permission)

    def remove(self, role_id: str, permission_id: str) -> None:
        statement = delete(RolePermissionModel).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.permission_id == permission_id,
        )
        self.session.execute(statement)
