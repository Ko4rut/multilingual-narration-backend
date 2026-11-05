from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.offline.models.offline_package import OfflinePackageStatus


class OfflinePackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str | None
    region_id: str
    language_id: str
    package_key: str
    package_name: str
    package_url: str | None
    package_version: int
    total_size: int | None
    package_checksum_sha256: str | None
    package_status: OfflinePackageStatus
    schema_version: int
    created_at: datetime
    last_updated_at: datetime
    published_at: datetime | None
