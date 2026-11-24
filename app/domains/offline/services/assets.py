"""Verify release assets against actual bytes, not just stored database metadata.

Locally managed audio/images are checked on the mounted volume; external
resources reuse the POI domain's public-URL validators.
"""

from hashlib import sha256
from pathlib import Path
import re

from app.core.config import Settings
from app.domains.offline.utils.manifest_diff import AssetDownload
from app.domains.poi.providers.audio_asset import RemoteAudioAssetProvider
from app.domains.poi.providers.image_checksum import RemoteImageChecksumProvider
from app.domains.poi.providers.poi_image import IMAGE_FILENAME_PATTERN


_AUDIO_FILE = re.compile(r"^[0-9a-f]{64}\.mp3$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")


class OfflineAssetVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.remote_audio = RemoteAudioAssetProvider()
        self.remote_image = RemoteImageChecksumProvider()

    @staticmethod
    def _verify_file(path: Path, expected_sha256: str, expected_size: int | None,
                     limit: int) -> bool:
        try:
            size = 0
            digest = sha256()
            with path.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    size += len(chunk)
                    if size > limit:
                        return False
                    digest.update(chunk)
            return size > 0 and (expected_size is None or size == expected_size) \
                and digest.hexdigest() == expected_sha256
        except OSError:
            return False

    def verify(self, asset: AssetDownload) -> bool:
        checksum = asset.sha256
        if not checksum or not _CHECKSUM.fullmatch(checksum.lower()):
            return False
        checksum = checksum.lower()
        if asset.kind == "audio":
            prefix = self.settings.tts_audio_public_base_url.rstrip("/") + "/"
            if asset.url.startswith(prefix):
                filename = asset.url[len(prefix):]
                return bool(_AUDIO_FILE.fullmatch(filename)) and self._verify_file(
                    self.settings.tts_audio_dir / filename, checksum,
                    asset.size, 100 * 1024 * 1024,
                )
            try:
                verified = self.remote_audio.verify(asset.url)
                return verified.checksum_sha256 == checksum and (
                    asset.size is None or verified.size == asset.size
                )
            except Exception:
                return False
        if asset.kind == "image":
            prefix = self.settings.poi_image_public_base_url.rstrip("/") + "/"
            if asset.url.startswith(prefix):
                filename = asset.url[len(prefix):]
                return bool(IMAGE_FILENAME_PATTERN.fullmatch(filename)) and self._verify_file(
                    self.settings.poi_image_dir / filename, checksum,
                    None, 10 * 1024 * 1024,
                )
            try:
                return self.remote_image.calculate(asset.url) == checksum
            except Exception:
                return False
        return False
