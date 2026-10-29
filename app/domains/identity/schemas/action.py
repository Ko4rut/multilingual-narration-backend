from pydantic import BaseModel, ConfigDict


class ActionRead(BaseModel):
    # Model để đọc dữ liệu hành động từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật hành động.
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
