from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.action import ActionModel
from app.domains.identity.models.management_function import ManagementFunctionModel
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role_permission import RolePermissionModel


class PermissionRepository:

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, permission_id: str) -> PermissionModel | None:
        # Lấy permission theo ID.
        return self.session.get(PermissionModel, permission_id)

    def get_all(self) -> list[PermissionModel]:
        # Lấy toàn bộ permission theo thứ tự ID ổn định.
        return list(self.session.scalars(select(PermissionModel).order_by(PermissionModel.id)))

    def get_all_by_role_id(self, role_id: str) -> list[PermissionModel]:
        # Lấy toàn bộ permission đã được gán cho một role.
        return list(self.session.scalars(select(PermissionModel)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .where(RolePermissionModel.role_id == role_id)
            .order_by(PermissionModel.id))
        )

    def role_has_permission(self, role_id: str, *, function_name: str, action_name: str) -> bool:
        # Kiểm tra role có quyền theo cặp chức năng và hành động hay không.
        statement = (
            select(PermissionModel.id)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .join(
                ManagementFunctionModel,
                ManagementFunctionModel.id == PermissionModel.function_id,
            )
            .join(ActionModel, ActionModel.id == PermissionModel.action_id)
            .where(
                RolePermissionModel.role_id == role_id,
                ManagementFunctionModel.name == function_name,
                ActionModel.name == action_name,
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None
