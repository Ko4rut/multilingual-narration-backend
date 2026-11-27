"""DTOs for central POI Category administration.

Category codes appear in published offline package keys. The API deliberately
does not support updating a Category code after creation.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_category_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError("category_name must not be empty")
    if len(name) > 120:
        raise ValueError("category_name must not exceed 120 characters")
    return name


class PoiCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_name: str
    category_code: str


class PoiCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(min_length=1, max_length=120)
    category_code: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    _normalize_name = field_validator("category_name")(normalize_category_name)


class PoiCategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_name: str = Field(min_length=1, max_length=120)

    _normalize_name = field_validator("category_name")(normalize_category_name)
