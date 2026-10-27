from app.domains.identity.models.action import ActionModel
from app.domains.identity.models.management_function import ManagementFunctionModel
from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role import RoleModel
from app.domains.identity.models.role_permission import RolePermissionModel
from app.domains.identity.models.user_session import UserSessionModel

# Compatibility aliases used by the ORM registry, seed, and existing callers.
Action = ActionModel
ManagementFunction = ManagementFunctionModel
ManagerUser = ManagerUserModel
Permission = PermissionModel
Role = RoleModel
RolePermission = RolePermissionModel
UserSession = UserSessionModel

__all__ = [
    "Action",
    "ManagementFunction",
    "ManagerUser",
    "Permission",
    "Role",
    "RolePermission",
    "UserSession",
    "ActionModel",
    "ManagementFunctionModel",
    "ManagerUserModel",
    "ManagerUserStatus",
    "PermissionModel",
    "RoleModel",
    "RolePermissionModel",
    "UserSessionModel",
]
