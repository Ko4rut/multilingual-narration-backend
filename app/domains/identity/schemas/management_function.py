from pydantic import BaseModel, ConfigDict


class ManagementFunctionRead(BaseModel):
    # Model để đọc dữ liệu chức năng quản lý từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật chức năng quản lý.
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
