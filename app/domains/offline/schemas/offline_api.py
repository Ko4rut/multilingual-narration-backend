"""Request and response contracts for Offline Group 3 HTTP endpoints."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.offline.schemas.offline_package import OfflinePackageRead
from app.domains.offline.services.offline import OfflineRebuildPlan


class OfflinePackagePrepareRequest(BaseModel):
    region_id: str = Field(min_length=1, max_length=50)
    language_id: str = Field(min_length=1, max_length=50)
    category_id: str | None = Field(default=None, min_length=1, max_length=50)


class OfflinePackagePreparationRead(BaseModel):
    package: OfflinePackageRead
    manifest: dict[str, Any]


class OfflineRebuildPreviewRequest(BaseModel):
    published_manifest: str = Field(
        min_length=1, max_length=4_194_304,
        description="Exact UTF-8 JSON text of the previously published manifest; its SHA-256 must match the database.",
    )


class OfflineAssetDownloadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    url: str
    sha256: str | None
    size: int | None


class OfflineManifestChangesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    added_poi_ids: tuple[str, ...]
    removed_poi_ids: tuple[str, ...]
    updated_poi_ids: tuple[str, ...]
    assets_to_download: tuple[OfflineAssetDownloadRead, ...]
    metadata_changed: bool
    changed: bool


class OfflineRebuildPreviewRead(BaseModel):
    package_id: str
    expected_version: int
    needs_rebuild: bool
    changes: OfflineManifestChangesRead
    proposed_manifest: dict[str, Any] | None

    @classmethod
    def from_plan(cls, plan: OfflineRebuildPlan) -> "OfflineRebuildPreviewRead":
        return cls(
            package_id=plan.package_id,
            expected_version=plan.expected_version,
            needs_rebuild=plan.needs_rebuild,
            changes=OfflineManifestChangesRead.model_validate(plan.changes),
            proposed_manifest=json.loads(plan.manifest) if plan.manifest is not None else None,
        )
