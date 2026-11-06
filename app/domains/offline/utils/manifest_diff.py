"""Compare published and proposed offline snapshots without storing extra hashes.

Only package_version and generated_at are volatile. Every other manifest field
is part of the payload contract and can trigger a rebuild. Asset SHA-256 values
already present in the source tables enable incremental mobile downloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


class InvalidOfflineManifest(ValueError):
    """A manifest cannot be trusted as a published baseline."""


@dataclass(frozen=True)
class AssetDownload:
    kind: str
    url: str
    sha256: str | None
    size: int | None


@dataclass(frozen=True)
class ManifestChanges:
    added_poi_ids: tuple[str, ...]
    removed_poi_ids: tuple[str, ...]
    updated_poi_ids: tuple[str, ...]
    assets_to_download: tuple[AssetDownload, ...]
    metadata_changed: bool = False

    @property
    def changed(self) -> bool:
        return bool(
            self.added_poi_ids or self.removed_poi_ids
            or self.updated_poi_ids or self.metadata_changed
        )


def load_manifest(payload: bytes) -> dict[str, Any]:
    """Parse a manifest and reject malformed/ambiguous membership."""
    try:
        document = json.loads(payload)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise InvalidOfflineManifest("Manifest is not valid JSON") from exc
    if not isinstance(document, dict):
        raise InvalidOfflineManifest("Manifest must be a JSON object")
    for field in (
        "schema_version", "package_key", "package_version",
        "region_code", "language_code", "category_code", "items",
    ):
        if field not in document:
            raise InvalidOfflineManifest(f"Manifest is missing {field}")
    if document["schema_version"] != 1 or type(document["package_version"]) is not int:
        raise InvalidOfflineManifest("Unsupported manifest schema or package version")
    if document["package_version"] < 1:
        raise InvalidOfflineManifest("Manifest package version must be positive")
    if not isinstance(document["items"], list):
        raise InvalidOfflineManifest("Manifest items must be an array")

    seen_pois: set[str] = set()
    seen_contents: set[str] = set()
    for item in document["items"]:
        if not isinstance(item, dict):
            raise InvalidOfflineManifest("Manifest item must be an object")
        poi_id = item.get("poi_id")
        content_id = item.get("content_id")
        if not isinstance(poi_id, str) or not poi_id:
            raise InvalidOfflineManifest("Missing POI ID in manifest item")
        if not isinstance(content_id, str) or not content_id:
            raise InvalidOfflineManifest("Missing content ID in manifest item")
        if poi_id in seen_pois or content_id in seen_contents:
            raise InvalidOfflineManifest("Duplicate POI or content in manifest")
        if type(item.get("content_version")) is not int or item["content_version"] < 1:
            raise InvalidOfflineManifest("Invalid content version in manifest item")
        if not isinstance(item.get("audio"), dict):
            raise InvalidOfflineManifest("Manifest item lacks audio metadata")
        if item.get("image") is not None and not isinstance(item["image"], dict):
            raise InvalidOfflineManifest("Manifest image metadata must be an object")
        seen_pois.add(poi_id)
        seen_contents.add(content_id)
    return document


def validate_published_manifest(
    payload: bytes, *, expected_checksum: str, expected_key: str,
    expected_version: int, expected_schema_version: int,
) -> dict[str, Any]:
    """Verify the actual previously published bytes, not current ORM rows."""
    if sha256(payload).hexdigest() != expected_checksum.lower():
        raise InvalidOfflineManifest("Published manifest SHA-256 does not match database")
    document = load_manifest(payload)
    if (
        document["package_key"] != expected_key
        or document["package_version"] != expected_version
        or document["schema_version"] != expected_schema_version
    ):
        raise InvalidOfflineManifest("Published manifest metadata does not match package")
    return document


def _items_by_poi(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["poi_id"]: item for item in document["items"]}


def _asset_refs(document: dict[str, Any]) -> list[AssetDownload]:
    found: list[AssetDownload] = []
    for item in document["items"]:
        for kind in ("audio", "image"):
            asset = item.get(kind)
            if asset is None:
                continue
            url = asset.get("url")
            if not isinstance(url, str) or not url:
                raise InvalidOfflineManifest(f"Missing {kind} URL")
            checksum = asset.get("sha256")
            if checksum is not None and not isinstance(checksum, str):
                raise InvalidOfflineManifest(f"Invalid {kind} checksum")
            size = asset.get("size") if kind == "audio" else None
            if size is not None and (type(size) is not int or size < 0):
                raise InvalidOfflineManifest("Invalid audio size")
            found.append(AssetDownload(kind, url, checksum.lower() if checksum else None, size))
    return found


def compare_manifests(
    published: dict[str, Any], proposed: dict[str, Any],
) -> ManifestChanges:
    """Detect only content changes, ignoring version and generation timestamp.

    A new asset whose checksum already exists in the old snapshot is reusable.
    Images without a checksum cannot be safely deduplicated by content.
    """
    old_items = _items_by_poi(published)
    new_items = _items_by_poi(proposed)
    old_ids, new_ids = set(old_items), set(new_items)
    added = tuple(sorted(new_ids - old_ids))
    removed = tuple(sorted(old_ids - new_ids))
    updated = tuple(sorted(
        poi_id for poi_id in old_ids & new_ids
        if old_items[poi_id] != new_items[poi_id]
    ))
    excluded = {"generated_at", "package_version", "items"}
    old_metadata = {k: v for k, v in published.items() if k not in excluded}
    new_metadata = {k: v for k, v in proposed.items() if k not in excluded}
    metadata_changed = old_metadata != new_metadata

    changes = bool(added or removed or updated or metadata_changed)
    missing: list[AssetDownload] = []
    if changes:
        old_checksums = {
            (a.kind, a.sha256) for a in _asset_refs(published) if a.sha256
        }
        seen_assets: set[tuple[str, str]] = set()
        for asset in _asset_refs(proposed):
            identity = (asset.kind, asset.sha256 or asset.url)
            if identity in seen_assets:
                continue
            seen_assets.add(identity)
            if asset.sha256 and (asset.kind, asset.sha256) in old_checksums:
                continue
            missing.append(asset)
    return ManifestChanges(added, removed, updated, tuple(missing), metadata_changed)

def manifest_assets(document: dict[str, Any]) -> tuple[AssetDownload, ...]:
    """All distinct assets in a proposed snapshot, for release-time verification."""
    seen: set[tuple[str, str]] = set()
    result: list[AssetDownload] = []
    for asset in _asset_refs(document):
        identity = (asset.kind, asset.sha256 or asset.url)
        if identity not in seen:
            seen.add(identity)
            result.append(asset)
    return tuple(result)
