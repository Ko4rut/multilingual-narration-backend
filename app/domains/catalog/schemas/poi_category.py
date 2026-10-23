from pydantic import BaseModel, ConfigDict


class PoiCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_name: str
    category_code: str
