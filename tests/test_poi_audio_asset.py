import socket
from types import SimpleNamespace

import httpx
import pytest

from app.domains.poi.exceptions import InvalidAudioAsset
from app.domains.poi.providers.audio_asset import RemoteAudioAssetProvider


def public_resolver(host: str, port: int, *, type: int):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def test_audio_provider_rejects_private_destination() -> None:
    provider = RemoteAudioAssetProvider(
        resolver=lambda host, port, *, type: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))
        ]
    )
    with pytest.raises(InvalidAudioAsset, match="public address"):
        provider.verify("https://assets.example/audio.mp3")


def test_audio_provider_rejects_unsupported_mime() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/plain"}, content=b"no")
    )
    provider = RemoteAudioAssetProvider(
        client=httpx.Client(transport=transport), resolver=public_resolver,
    )
    with pytest.raises(InvalidAudioAsset, match="unsupported MIME"):
        provider.verify("https://assets.example/audio.mp3")


def test_audio_provider_derives_metadata_from_downloaded_bytes(monkeypatch) -> None:
    audio_bytes = b"verified-audio-bytes"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "audio/mpeg"}, content=audio_bytes,
        )
    )
    monkeypatch.setattr(
        "app.domains.poi.providers.audio_asset.MutagenFile",
        lambda stream: SimpleNamespace(info=SimpleNamespace(length=12.2)),
    )
    provider = RemoteAudioAssetProvider(
        client=httpx.Client(transport=transport), resolver=public_resolver,
    )

    result = provider.verify("https://assets.example/audio.mp3")

    assert result.size == len(audio_bytes)
    assert result.duration_sec == 13
    assert result.mime_type == "audio/mpeg"
    assert len(result.checksum_sha256) == 64
