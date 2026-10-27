from hashlib import sha256

import pytest

from app.domains.identity.security.refresh_token import SecureRefreshTokenProvider


def test_issue_refresh_token_returns_only_token_and_sha256_hash():
    requested_bytes = []
    provider = SecureRefreshTokenProvider(
        token_factory=lambda token_bytes: (
            requested_bytes.append(token_bytes) or "opaque-refresh-token"
        )
    )

    issued = provider.issue_refresh_token()

    assert issued.token == "opaque-refresh-token"
    assert issued.token_hash == sha256(b"opaque-refresh-token").hexdigest()
    assert requested_bytes == [32]


def test_refresh_token_hash_is_deterministic_without_normalizing_token():
    provider = SecureRefreshTokenProvider()

    assert provider.hash_refresh_token(" token ") == sha256(b" token ").hexdigest()
    assert provider.hash_refresh_token(" token ") != provider.hash_refresh_token(
        "token"
    )


def test_refresh_token_provider_rejects_weak_or_empty_tokens():
    with pytest.raises(ValueError, match="at least 32"):
        SecureRefreshTokenProvider(token_bytes=31)

    provider = SecureRefreshTokenProvider(token_factory=lambda _token_bytes: "")
    with pytest.raises(ValueError, match="empty"):
        provider.issue_refresh_token()
