"""Persistent, immutable *staging* storage for generated offline manifests.

This writes JSON bytes to disk, not to PostgreSQL. A staged file is not a
published resource and must not be exposed through a public static mount.
Publication and asset verification are deliberately separate operations.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.domains.offline.utils.manifest_diff import InvalidOfflineManifest, load_manifest


_PACKAGE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,49}\Z")


class ManifestStorageConflict(ValueError):
    """An immutable path already contains different bytes."""


class ManifestStorageNotFound(FileNotFoundError):
    """No manifest has been staged for that package/version."""


class ManifestStorageCorrupt(ValueError):
    """Stored manifest is invalid or differs from an expected checksum."""


@dataclass(frozen=True)
class StagedManifest:
    path: Path
    sha256: str
    size: int


class FileSystemManifestStorage:
    """Local filesystem staging, intended to be backed by a persistent volume.

    Files are staged at <root>/staging/<package_id>/vN/manifest.json.
    Writes use a temporary file and an atomic, no-overwrite hard link so
    a version can never silently change, even between concurrent writers.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def _path(self, package_id: str, version: int) -> Path:
        if not isinstance(package_id, str) or not _PACKAGE_ID_RE.fullmatch(package_id):
            raise ValueError("Invalid offline package ID")
        if type(version) is not int or version < 1:
            raise ValueError("Manifest version must be a positive integer")
        return self.root / "staging" / package_id / f"v{version}" / "manifest.json"

    def save_staged(self, package_id: str, version: int, payload: bytes) -> StagedManifest:
        """Persist manifest bytes without overwriting an existing version.

        A DB transaction that fails after this call can leave an orphan staged
        file; it remains private and can be cleaned up explicitly later.
        """
        if not isinstance(payload, bytes):
            raise TypeError("Manifest payload must be bytes")
        target = self._path(package_id, version)
        doc = load_manifest(payload)
        if doc["package_version"] != version:
            raise InvalidOfflineManifest("Manifest version differs from storage path")

        digest = sha256(payload).hexdigest()
        result = StagedManifest(path=target, sha256=digest, size=len(payload))
        target.parent.mkdir(parents=True, exist_ok=True)

        # Existing immutable content can be safely reused on retries.
        if target.exists():
            if target.read_bytes() == payload:
                return result
            raise ManifestStorageConflict("Staged manifest version already has different content")

        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=".manifest-", suffix=".tmp", dir=target.parent,
        )
        try:
            with os.fdopen(file_descriptor, "wb") as temp_file:
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            try:
                os.link(temp_name, target)
            except FileExistsError:
                # Another process won the race: accept only identical bytes.
                if target.read_bytes() != payload:
                    raise ManifestStorageConflict(
                        "Staged manifest version already has different content"
                    ) from None
        finally:
            os.unlink(temp_name)
        return result

    def read_staged(
        self, package_id: str, version: int, *, expected_sha256: str | None = None,
    ) -> bytes:
        """Internal read only; never serve staging files to unauthenticated mobile."""
        target = self._path(package_id, version)
        try:
            payload = target.read_bytes()
        except FileNotFoundError as exc:
            raise ManifestStorageNotFound(
                "Staged manifest does not exist"
            ) from exc
        try:
            document = load_manifest(payload)
        except InvalidOfflineManifest as exc:
            raise ManifestStorageCorrupt("Stored manifest is invalid") from exc
        if document["package_version"] != version:
            raise ManifestStorageCorrupt("Stored manifest version differs from storage path")
        if expected_sha256 is not None and sha256(payload).hexdigest() != expected_sha256.lower():
            raise ManifestStorageCorrupt("Stored manifest SHA-256 mismatch")
        return payload
