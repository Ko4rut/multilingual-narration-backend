from app.core.exceptions import ResourceNotFound


class RoleNotFound(ResourceNotFound):
    """Không tìm thấy vai trò được yêu cầu."""


class PermissionNotFound(ResourceNotFound):
    """Không tìm thấy một quyền được yêu cầu khi cấu hình vai trò."""


class RoleNameAlreadyExists(Exception):
    """Tên vai trò đã được sử dụng."""
