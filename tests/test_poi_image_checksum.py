from hashlib import sha256
import socket

import httpx
import pytest

from app.domains.poi.exceptions import InvalidPoiImage
from app.domains.poi.providers.image_checksum import RemoteImageChecksumProvider


def public_resolver(host: str, port: int, *, type: int):
    return [(socket.AF_INET, type, 6, "", ("93.184.216.34", port))]


def private_resolver(host: str, port: int, *, type: int):
    return [(socket.AF_INET, type, 6, "", ("127.0.0.1", port))]


def test_calculate_hashes_downloaded_image_bytes() -> None:
    image_bytes = b"fake-image-content"

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "image/webp"}, content=image_bytes)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = RemoteImageChecksumProvider(client=client, resolver=public_resolver)
        result = provider.calculate("https://images.example/poi.webp")

    assert result == sha256(image_bytes).hexdigest()


def test_calculate_rejects_private_network_destination() -> None:
    provider = RemoteImageChecksumProvider(resolver=private_resolver)

    with pytest.raises(InvalidPoiImage, match="public address"):
        provider.calculate("http://127.0.0.1/private.png")


def test_calculate_rejects_non_image_response() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"not image")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = RemoteImageChecksumProvider(client=client, resolver=public_resolver)
        with pytest.raises(InvalidPoiImage, match="image MIME type"):
            provider.calculate("https://images.example/not-image")
