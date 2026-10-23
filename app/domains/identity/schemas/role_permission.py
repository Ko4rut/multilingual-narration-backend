from pydantic import BaseModel, ConfigDict


class RolePermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: str
    permission_id: str
