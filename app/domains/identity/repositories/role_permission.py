from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.identity.models.role_permission import RolePermissionModel


class RolePermissionRepository:

    def __init__(self, session: Session):
        self.session = session

    def exists(self, role_id: str, permission_id: str) -> bool:
        # Kiểm tra một permission đã được gán cho role hay chưa.
        statement = select(RolePermissionModel.role_id).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.permission_id == permission_id,
        )
        return self.session.scalar(statement) is not None

    def get_all_by_role_id(self, role_id: str) -> list[RolePermissionModel]:
        # Lấy các liên kết permission của role theo thứ tự permission ID.
        return list(self.session.scalars(
            select(RolePermissionModel)
            .where(RolePermissionModel.role_id == role_id)
            .order_by(RolePermissionModel.permission_id)
        ))

    def add(self, role_permission: RolePermissionModel) -> None:
        # Đưa liên kết role-permission mới vào Session, không tự commit.
        self.session.add(role_permission)

    def remove(self, role_id: str, permission_id: str) -> None:
        # Xóa liên kết giữa role và permission trong transaction hiện tại.
        statement = delete(RolePermissionModel).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.permission_id == permission_id,
        )
        self.session.execute(statement)
