from pydantic import BaseModel, ConfigDict


class PoiCategoryMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    poi_id: str
    poi_category_id: str
