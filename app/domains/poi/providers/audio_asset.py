"""Tải và xác minh audio từ mạng công khai trước khi lưu metadata."""

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from ipaddress import ip_address
from math import ceil
import socket
from urllib.parse import urlsplit

import httpx
from mutagen import File as MutagenFile, MutagenError

from app.domains.poi.exceptions import InvalidAudioAsset


ALLOWED_AUDIO_MIME_TYPES = {
    "audio/mpeg", "audio/aac", "audio/ogg", "audio/wav", "audio/mp4", "audio/webm",
}
MAX_AUDIO_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class VerifiedAudioAsset:
    url: str
    size: int
    duration_sec: int
    mime_type: str
    checksum_sha256: str


class RemoteAudioAssetProvider:
    """Xác minh URL công khai và tính metadata từ bytes audio thực tế."""

    def __init__(self, *, client: httpx.Client | None = None,
                 resolver: Callable[..., list[tuple]] = socket.getaddrinfo,
                 max_bytes: int = MAX_AUDIO_BYTES) -> None:
        self.client = client
        self.resolver = resolver
        self.max_bytes = max_bytes

    def verify(self, url: str) -> VerifiedAudioAsset:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        if hostname is None:
            raise InvalidAudioAsset("Audio URL must include a hostname")
        self._require_public_host(hostname, parsed.port or (80 if parsed.scheme == "http" else 443))
        client = self.client or httpx.Client(timeout=30.0, follow_redirects=False)
        owns_client = self.client is None
        try:
            with client.stream("GET", url) as response:
                if 300 <= response.status_code < 400:
                    raise InvalidAudioAsset("Audio URL must not redirect")
                response.raise_for_status()
                mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
                    raise InvalidAudioAsset("Audio URL returned an unsupported MIME type")
                output = BytesIO()
                digest = sha256()
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise InvalidAudioAsset("Audio exceeds the 100 MiB limit")
                    output.write(chunk)
                    digest.update(chunk)
                if size == 0:
                    raise InvalidAudioAsset("Audio asset must not be empty")
                output.seek(0)
                parsed_audio = MutagenFile(output)
                duration = ceil(getattr(getattr(parsed_audio, "info", None), "length", 0))
                if duration <= 0:
                    raise InvalidAudioAsset("Unable to determine audio duration")
                return VerifiedAudioAsset(
                    url=url, size=size, duration_sec=duration, mime_type=mime_type,
                    checksum_sha256=digest.hexdigest(),
                )
        except InvalidAudioAsset:
            raise
        except (httpx.HTTPError, MutagenError, OSError, ValueError) as exc:
            raise InvalidAudioAsset("Unable to download or inspect audio asset") from exc
        finally:
            if owns_client:
                client.close()

    def _require_public_host(self, hostname: str, port: int) -> None:
        try:
            addresses = self.resolver(hostname, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise InvalidAudioAsset("Unable to resolve audio hostname") from exc
        if not addresses:
            raise InvalidAudioAsset("Unable to resolve audio hostname")
        if any(not ip_address(address[4][0]).is_global for address in addresses):
            raise InvalidAudioAsset("Audio URL must resolve to a public address")
