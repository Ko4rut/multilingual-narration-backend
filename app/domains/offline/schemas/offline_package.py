from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfflinePackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str | None
    region_id: str
    language_id: str
    package_key: str
    package_name: str
    package_url: str
    package_version: int
    total_size: int
    package_checksum_sha256: str
    package_status: str
    schema_version: int
    created_at: datetime
    last_updated_at: datetime
    published_at: datetime | None
