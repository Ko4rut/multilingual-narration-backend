from pydantic import BaseModel, ConfigDict


class RolePermissionRead(BaseModel):
    # Model để đọc dữ liệu quyền của vai trò từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật quyền của vai trò.
    model_config = ConfigDict(from_attributes=True)

    role_id: str
    permission_id: str
