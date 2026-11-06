"""Deterministic, versioned offline manifest serialization.

No files are uploaded here. The caller must verify source assets, store the
returned bytes at an immutable URL, and verify the manifest before publish.
"""

import json
from datetime import datetime, timezone
from hashlib import sha256

from app.domains.offline.repositories.offline_package_item import OfflineCandidate


def manifest_bytes(
    *, package_key: str, package_version: int, region_code: str,
    language_code: str, category_code: str | None,
    candidates: list[OfflineCandidate], generated_at: datetime,
) -> bytes:
    if package_version < 1:
        raise ValueError("package_version must be positive")
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")

    items = []
    seen_content_ids: set[str] = set()
    for candidate in sorted(candidates, key=lambda c: (c.poi.id, c.content.id)):
        poi, content, audio = candidate.poi, candidate.content, candidate.audio
        if content.id in seen_content_ids:
            raise ValueError("Duplicate content in manifest")
        seen_content_ids.add(content.id)
        if content.poi_id != poi.id or audio.poi_content_id != content.id:
            raise ValueError("Inconsistent POI/content/audio references")
        if content.content_version < 1 or audio.audio_size <= 0:
            raise ValueError("Invalid content version or audio size")
        items.append({
            "poi_id": poi.id,
            "poi_name": poi.poi_name,
            "poi_location": poi.poi_location,
            "latitude": str(poi.latitude),
            "longitude": str(poi.longitude),
            "trigger_radius_meter": str(poi.trigger_radius_meter),
            "content_id": content.id,
            "content_version": content.content_version,
            "narration_title": content.narration_title,
            "narration_script": content.narration_script,
            "audio": {
                "url": audio.audio_url,
                "size": audio.audio_size,
                "mime_type": audio.audio_mime_type,
                "duration_sec": audio.audio_duration_sec,
                "sha256": audio.audio_checksum_sha256.lower(),
            },
            "image": (
                {"url": poi.poi_image_url,
                 "sha256": (poi.image_checksum_sha256.lower()
                            if poi.image_checksum_sha256 else None)}
                if poi.poi_image_url else None
            ),
        })

    document = {
        "schema_version": 1,
        "package_key": package_key,
        "package_version": package_version,
        "region_code": region_code,
        "language_code": language_code,
        "category_code": category_code,
        "generated_at": generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "items": items,
    }
    return (json.dumps(document, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def manifest_sha256(data: bytes) -> str:
    return sha256(data).hexdigest()
