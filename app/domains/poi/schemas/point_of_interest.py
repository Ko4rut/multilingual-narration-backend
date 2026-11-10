from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator,
)

from app.domains.catalog.schemas.poi_category import PoiCategoryRead
from app.domains.catalog.schemas.region import RegionRead


class PoiRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    region_id: str
    poi_name: str
    poi_image_url: str
    image_checksum_sha256: str | None
    poi_qr_code: str
    poi_location: str
    poi_status: str
    latitude: Decimal
    longitude: Decimal
    trigger_radius_meter: Decimal
    created_at: datetime
    last_updated_at: datetime


class PoiPage(BaseModel):
    items: list[PoiRead]
    total: int
    offset: int
    limit: int


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
ImageUrl = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Checksum = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{64}$")]
Latitude = Annotated[Decimal, Field(ge=-90, le=90, max_digits=9, decimal_places=6, allow_inf_nan=False)]
Longitude = Annotated[Decimal, Field(ge=-180, le=180, max_digits=9, decimal_places=6, allow_inf_nan=False)]
Radius = Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2, allow_inf_nan=False)]
CategoryIds = Annotated[list[Identifier], Field(max_length=100)]
PoiStatus = Literal["ACTIVE", "INACTIVE"]


class PoiWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("poi_image_url", check_fields=False)
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("poi_image_url must be an HTTP(S) asset URL without credentials")
        return value

    @field_validator("category_ids", check_fields=False)
    @classmethod
    def unique_categories(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("category_ids must not contain duplicates")
        return value

    @field_validator("image_checksum_sha256", check_fields=False)
    @classmethod
    def normalize_checksum(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None


class PoiCreate(PoiWrite):
    region_id: Identifier
    poi_name: Name
    poi_location: Location
    poi_qr_code: Name
    poi_image_url: ImageUrl
    image_checksum_sha256: Checksum | None = None
    latitude: Latitude
    longitude: Longitude
    trigger_radius_meter: Radius
    category_ids: CategoryIds = Field(default_factory=list)
    poi_status: Literal["INACTIVE"] = "INACTIVE"


class PoiUpdate(PoiWrite):
    region_id: Identifier | None = None
    poi_name: Name | None = None
    poi_location: Location | None = None
    poi_qr_code: Name | None = None
    poi_image_url: ImageUrl | None = None
    image_checksum_sha256: Checksum | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    trigger_radius_meter: Radius | None = None
    category_ids: CategoryIds | None = None
    poi_status: PoiStatus | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "PoiUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for name in self.model_fields_set - {"image_checksum_sha256"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} must not be null")
        return self


class PoiStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poi_status: PoiStatus


class AdminPoiRead(PoiRead):
    poi_status: PoiStatus
    created_by: str
    last_updated_by: str
    category_ids: list[str] = Field(default_factory=list)
    can_activate: bool = False


class AdminPoiPage(BaseModel):
    items: list[AdminPoiRead]
    total: int
    offset: int
    limit: int


class PoiFormOptions(BaseModel):
    regions: list[RegionRead]
    categories: list[PoiCategoryRead]
