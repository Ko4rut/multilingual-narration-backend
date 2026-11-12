"""Tải ảnh POI an toàn và tính checksum SHA-256 từ bytes thực tế."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from ipaddress import ip_address
import socket
from urllib.parse import urlsplit

import httpx

from app.domains.poi.exceptions import InvalidPoiImage
from app.domains.poi.providers.poi_image import FileSystemPoiImageStorage


# Giới hạn dung lượng giúp tránh tải ảnh quá lớn vào hạ tầng backend.
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class PoiImageChecksumProvider:
    """Đọc checksum ảnh nội bộ hoặc xác minh ảnh URL bên ngoài."""

    def __init__(
        self,
        storage: FileSystemPoiImageStorage,
        remote: "RemoteImageChecksumProvider | None" = None,
    ) -> None:
        self.storage = storage
        self.remote = remote or RemoteImageChecksumProvider()

    def calculate(self, url: str) -> str:
        managed_checksum = self.storage.get_checksum(url)
        if managed_checksum is not None:
            return managed_checksum
        return self.remote.calculate(url)


class RemoteImageChecksumProvider:
    """Tải ảnh từ mạng công khai và tính SHA-256 mà không giữ toàn bộ trong RAM.
    Provider chủ động chặn địa chỉ nội bộ/loopback và redirect để giảm nguy cơ
    SSRF. Checksum được tính từ bytes ảnh thực tế, không tính từ chuỗi URL.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        resolver: Callable[..., list[tuple]] = socket.getaddrinfo,
        max_bytes: int = MAX_IMAGE_BYTES,
    ) -> None:
        # Cho phép inject HTTP client và DNS resolver để cấu hình hoặc kiểm thử.
        self.client = client
        self.resolver = resolver
        self.max_bytes = max_bytes

    def calculate(self, url: str) -> str:
        # Xác minh, tải tuần tự và trả checksum SHA-256 dạng hexadecimal.
        parsed = urlsplit(url)
        hostname = parsed.hostname
        if hostname is None:
            raise InvalidPoiImage("POI image URL must include a hostname")
        default_port = 443
        if parsed.scheme == "http":
            default_port = 80
        # Kiểm tra DNS trước khi phát request để từ chối mạng không công khai.
        self._require_public_host(hostname, parsed.port or default_port)

        client = self.client or httpx.Client(timeout=10.0, follow_redirects=False)
        owns_client = self.client is None
        try:
            with client.stream("GET", url) as response:
                # Không tự đi theo redirect vì đích mới có thể trỏ vào mạng nội bộ.
                if 300 <= response.status_code < 400:
                    raise InvalidPoiImage("POI image URL must not redirect")
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                if not content_type.lower().startswith("image/"):
                    raise InvalidPoiImage("POI image URL must return an image MIME type")
                digest = sha256()
                size = 0
                # Băm theo từng chunk để dung lượng RAM không tăng theo kích thước ảnh.
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise InvalidPoiImage("POI image exceeds the 10 MiB limit")
                    digest.update(chunk)
                if size == 0:
                    raise InvalidPoiImage("POI image must not be empty")
                return digest.hexdigest()
        except InvalidPoiImage:
            raise
        except (httpx.HTTPError, OSError) as exc:
            raise InvalidPoiImage("Unable to download POI image") from exc
        finally:
            if owns_client:
                client.close()

    def _require_public_host(self, hostname: str, port: int) -> None:
        """Yêu cầu mọi địa chỉ IP phân giải được đều là địa chỉ mạng công khai."""
        try:
            addresses = self.resolver(hostname, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise InvalidPoiImage("Unable to resolve POI image hostname") from exc
        if not addresses:
            raise InvalidPoiImage("Unable to resolve POI image hostname")
        for address in addresses:
            if not ip_address(address[4][0]).is_global:
                raise InvalidPoiImage("POI image URL must resolve to a public address")
