"""Preflight tests for the Hanoi offline demo; no database required."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_demo_offline_manifests import SPEC_PATH, audio_metadata, collect_audio


def test_recipe_has_two_packages_and_four_distinct_audio_files():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["region_code"] == "HAN"
    assert {p["package_key"] for p in spec["packages"]} == {
        "region:HAN|lang:vi", "region:HAN|lang:en"
    }
    entries = [(p["language_code"], item["poi_qr_code"], item["audio_file"])
               for p in spec["packages"] for item in p["items"]]
    assert len(entries) == 4
    assert {(lang, poi) for lang, poi, _ in entries} == {
        ("vi", "HAN-VAN-MIEU"), ("vi", "HAN-HO-GUOM"),
        ("en", "HAN-VAN-MIEU"), ("en", "HAN-HO-GUOM")
    }
    assert len({file for _, _, file in entries}) == 4


def test_real_file_hash_and_size(tmp_path: Path):
    content = b"ID3" + bytes(range(64))
    path = tmp_path / "example.mp3"
    path.write_bytes(content)
    assert audio_metadata(path) == {
        "audio_checksum": hashlib.sha256(content).hexdigest(),
        "audio_size": len(content),
    }


def test_missing_mp3_fails_before_db_access(tmp_path: Path):
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    with pytest.raises(FileNotFoundError, match="han-van-mieu-vi.mp3"):
        collect_audio(spec, tmp_path)


def test_compose_manifest_services_enabled_by_default():
    """Basic structure assertions without requiring Docker or PyYAML."""
    from pathlib import Path

    compose = (Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text()
    assert "  offline-manifest-init:" in compose
    assert "  media:" in compose
    assert "profiles:" not in compose
    assert "condition: service_completed_successfully" in compose
    assert "./fixtures:/app/fixtures" in compose
    assert "./fixtures/offline:/usr/share/nginx/html:ro" in compose
