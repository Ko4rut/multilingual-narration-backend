from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    # Model để đọc dữ liệu quyền từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật quyền.
    model_config = ConfigDict(from_attributes=True)

    id: str
    function_id: str
    action_id: str
