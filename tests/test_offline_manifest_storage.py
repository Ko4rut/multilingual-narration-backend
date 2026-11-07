"""Filesystem manifest staging contracts (no database required)."""

import json
from hashlib import sha256

import pytest

from app.domains.offline.storage.manifest import (
    FileSystemManifestStorage, ManifestStorageConflict,
    ManifestStorageCorrupt, ManifestStorageNotFound,
)
from app.domains.offline.utils.manifest_diff import InvalidOfflineManifest


def payload(version=1):
    return (json.dumps({
        "schema_version": 1,
        "package_key": "region:HAN|lang:vi",
        "package_version": version,
        "region_code": "HAN",
        "language_code": "vi",
        "category_code": None,
        "items": [],
    }, sort_keys=True) + "\n").encode("utf-8")


def test_save_and_read_immutable_manifest_and_survive_new_instance(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    raw = payload()
    saved = storage.save_staged("pack-071126-a1b2c3d4", 1, raw)
    expected = tmp_path / "staging" / "pack-071126-a1b2c3d4" / "v1" / "manifest.json"
    assert saved.path == expected
    assert saved.sha256 == sha256(raw).hexdigest()
    assert saved.size == len(raw)
    assert expected.read_bytes() == raw

    # Retry is idempotent; newly created adapter can still read persisted bytes.
    assert storage.save_staged("pack-071126-a1b2c3d4", 1, raw) == saved
    reopened = FileSystemManifestStorage(tmp_path)
    assert reopened.read_staged(
        "pack-071126-a1b2c3d4", 1, expected_sha256=saved.sha256,
    ) == raw


def test_versions_and_packages_are_distinct(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    storage.save_staged("pack-one", 1, payload(1))
    storage.save_staged("pack-one", 2, payload(2))
    storage.save_staged("pack-two", 1, payload(1))
    assert storage.read_staged("pack-one", 1) == payload(1)
    assert storage.read_staged("pack-one", 2) == payload(2)
    assert storage.read_staged("pack-two", 1) == payload(1)


def test_conflicting_same_version_does_not_replace_original(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    first = payload()
    storage.save_staged("pack-1", 1, first)
    other = first.replace(b'"language_code": "vi"', b'"language_code": "en"')
    with pytest.raises(ManifestStorageConflict):
        storage.save_staged("pack-1", 1, other)
    assert storage.read_staged("pack-1", 1) == first


@pytest.mark.parametrize("invalid_id", ("../etc", "/etc/passwd", "pack/a", "", "x" * 51, ".."))
def test_rejects_traversal_and_invalid_ids(tmp_path, invalid_id):
    storage = FileSystemManifestStorage(tmp_path)
    with pytest.raises(ValueError, match="Invalid offline package ID"):
        storage.save_staged(invalid_id, 1, payload())


@pytest.mark.parametrize("version", (0, -1, True, "2"))
def test_rejects_invalid_versions(tmp_path, version):
    with pytest.raises(ValueError, match="version"):
        FileSystemManifestStorage(tmp_path).save_staged("pack-1", version, payload())


def test_rejects_invalid_or_mismatched_json(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    with pytest.raises(InvalidOfflineManifest):
        storage.save_staged("pack-1", 2, payload(1))
    with pytest.raises(InvalidOfflineManifest):
        storage.save_staged("pack-1", 1, b'{"oops":true}')
    assert not list(tmp_path.rglob("manifest.json"))


def test_read_detects_corrupt_bytes_and_missing_file(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    raw = payload()
    saved = storage.save_staged("pack-1", 1, raw)
    with pytest.raises(ManifestStorageNotFound):
        storage.read_staged("pack-1", 2)
    with pytest.raises(ManifestStorageCorrupt, match="SHA-256"):
        storage.read_staged("pack-1", 1, expected_sha256="0" * 64)
    saved.path.write_bytes(b"garbage")
    with pytest.raises(ManifestStorageCorrupt):
        storage.read_staged("pack-1", 1)


def test_storage_failure_aborts_staging_transaction():
    """The service writes within its transaction, before leaving the context."""
    from unittest.mock import MagicMock
    from test_offline_repository import make_service
    storage = MagicMock()
    storage.save_staged.side_effect = OSError("disk full")
    service, session, _, _ = make_service()
    service.manifest_storage = storage
    with pytest.raises(OSError, match="disk full"):
        service.prepare_initial_package(region_id="region-1", language_id="lang-vi")
    storage.save_staged.assert_called_once()
    assert session.begin.return_value.__exit__.call_args.args[0] is OSError
