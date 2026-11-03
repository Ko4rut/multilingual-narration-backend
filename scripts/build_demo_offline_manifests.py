"""Generate bilingual Hanoi offline demo manifests from four real MP3 files.

Fixture generation only: no database updates, uploads or package publishing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "offline"
SPEC_PATH = FIXTURE_DIR / "hanoi-manifest-seed.json"


def audio_metadata(path: Path) -> dict:
    """Checksum and size are calculated from file bytes, not the URL."""
    if not path.is_file() or path.suffix.lower() != ".mp3":
        raise ValueError(f"Expected an MP3 file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if size == 0:
        raise ValueError(f"Empty MP3 file: {path}")
    return {"audio_checksum": digest.hexdigest(), "audio_size": size}


def collect_audio(spec: dict, audio_dir: Path) -> dict:
    names = [item["audio_file"] for pkg in spec["packages"] for item in pkg["items"]]
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError("Expected exactly four distinct audio files")
    if any(Path(name).name != name or not name.endswith(".mp3") for name in names):
        raise ValueError("Only .mp3 basenames are allowed in the seed")
    missing = [name for name in names if not (audio_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing MP3s in {audio_dir}: {', '.join(missing)}")
    return {name: audio_metadata(audio_dir / name) for name in names}


def exactly_one(rows: list, description: str):
    if len(rows) != 1:
        raise ValueError(f"{description}: expected exactly one row, got {len(rows)}")
    return rows[0]


def build_manifests(spec: dict, assets: dict, session, media_base_url: str) -> list:
    """Read seeded POI/content/audio IDs and scripts; never fabricate IDs."""
    from sqlalchemy import func, select
    from app.models import ContentAudio, Language, PoiContent, PointOfInterest, Region

    code = spec["region_code"]
    region = exactly_one(
        session.scalars(select(Region).where(Region.region_code == code)).all(),
        f"region {code}",
    )
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    output = []
    for package in spec["packages"]:
        lang_code = package["language_code"]
        expected_key = f"region:{code}|lang:{lang_code}"
        if package["package_key"] != expected_key:
            raise ValueError(f"Invalid package_key: {package['package_key']}")
        language = exactly_one(
            session.scalars(select(Language).where(Language.language_code == lang_code)).all(),
            f"language {lang_code}",
        )
        items = []
        for entry in package["items"]:
            poi = exactly_one(
                session.scalars(
                    select(PointOfInterest).where(
                        PointOfInterest.poi_qr_code == entry["poi_qr_code"]
                    )
                ).all(),
                f"POI {entry['poi_qr_code']}",
            )
            if poi.region_id != region.id or poi.poi_status.upper() != "ACTIVE":
                raise ValueError(f"POI is not ACTIVE in {code}: {poi.poi_qr_code}")
            content = exactly_one(
                session.scalars(
                    select(PoiContent).where(
                        PoiContent.poi_id == poi.id,
                        PoiContent.language_id == language.id,
                        func.upper(PoiContent.content_status) == "PUBLISHED",
                    )
                ).all(),
                f"published content for {poi.poi_qr_code}/{lang_code}",
            )
            audio = exactly_one(
                session.scalars(
                    select(ContentAudio).where(ContentAudio.poi_content_id == content.id)
                ).all(),
                f"audio for content {content.id}",
            )
            file_name = entry["audio_file"]
            metadata = assets[file_name]
            items.append({
                "poi_id": poi.id,
                "poi_name": poi.poi_name,
                "poi_location": poi.poi_location,
                "latitude": str(poi.latitude),
                "longitude": str(poi.longitude),
                "trigger_radius_meter": str(poi.trigger_radius_meter),
                "narration_id": content.id,
                "content_version": content.content_version,
                "narration_title": content.narration_title,
                "narration_script": content.narration_script,
                "audio_id": audio.id,
                "audio_url": f"{media_base_url.rstrip('/')}/audio/{quote(file_name)}",
                "audio_checksum": metadata["audio_checksum"],
                "audio_size": metadata["audio_size"],
            })
        output.append({
            "package_key": package["package_key"],
            "package_version": 1,
            "schema_version": spec["schema_version"],
            "region_code": code,
            "language_code": lang_code,
            "generated_at": timestamp,
            "items": items,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--media-base-url", required=True,
        help="HTTP(S) address that actually serves /audio/<name>.mp3",
    )
    parser.add_argument("--audio-dir", type=Path, default=FIXTURE_DIR / "audio")
    parser.add_argument("--output-dir", type=Path, default=FIXTURE_DIR / "generated")
    args = parser.parse_args()
    parsed_url = urlsplit(args.media_base_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        parser.error("--media-base-url must be an HTTP(S) URL with a host")

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assets = collect_audio(spec, args.audio_dir)

    from app.db import session_scope
    with session_scope() as session:
        manifests = build_manifests(spec, assets, session, args.media_base_url)

    outputs = []
    for manifest in manifests:
        lang = manifest["language_code"]
        path = args.output_dir / f"region-HAN-lang-{lang}" / "v1" / "manifest.json"
        payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        distinct_assets = {
            item["audio_checksum"]: item["audio_size"] for item in manifest["items"]
        }
        outputs.append((path, payload, {
            "package_key": manifest["package_key"],
            "manifest_path": str(path),
            "manifest_checksum_sha256": hashlib.sha256(payload).hexdigest(),
            "total_audio_size": sum(distinct_assets.values()),
            "status": "PREPARED_NOT_PUBLISHED",
        }))
    index_path = args.output_dir / "manifest-index-v1.json"
    target_paths = [path for path, _, _ in outputs]
    existing = [path for path in [*target_paths, index_path] if path.exists()]
    if existing:
        # Compose may rerun the one-shot init job. Reuse v1 only if every
        # persisted manifest still matches the current POI/content/audio bytes
        # and serving URL; never overwrite an immutable published URL.
        if len(existing) != len(target_paths) + 1:
            raise FileExistsError(
                "Incomplete v1 fixture output; move the incomplete generated "
                "directory aside before retrying. Existing: "
                + ", ".join(map(str, existing))
            )
        index = json.loads(index_path.read_text(encoding="utf-8"))
        by_key = {entry["package_key"]: entry for entry in index}
        if len(by_key) != len(outputs):
            raise ValueError("Existing manifest index is incomplete or duplicated")
        for path, _, expected in outputs:
            stored_bytes = path.read_bytes()
            stored = json.loads(stored_bytes)
            current = next(
                manifest for manifest in manifests
                if manifest["package_key"] == expected["package_key"]
            )
            # generated_at is informational; it may differ on a restart.
            current = {k: v for k, v in current.items() if k != "generated_at"}
            stored = {k: v for k, v in stored.items() if k != "generated_at"}
            entry = by_key.get(expected["package_key"])
            if (
                stored != current
                or entry is None
                or entry.get("manifest_checksum_sha256")
                != hashlib.sha256(stored_bytes).hexdigest()
                or entry.get("total_audio_size") != expected["total_audio_size"]
                or entry.get("status") != "PREPARED_NOT_PUBLISHED"
            ):
                raise FileExistsError(
                    f"Immutable v1 fixture no longer matches source assets: {path}. "
                    "Prepare a new package version; do not replace an existing v1."
                )
        print("Existing v1 manifests verified and reused (no files overwritten).")
    else:
        for path, payload, _ in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        index_path.write_text(
            json.dumps([data for _, _, data in outputs], ensure_ascii=False, indent=2)
            + "\\n",
            encoding="utf-8",
        )
        print("New v1 manifest fixtures created.")

    print("Manifest fixtures only, NOT published. Reconcile ContentAudio and storage first.")


if __name__ == "__main__":
    main()
