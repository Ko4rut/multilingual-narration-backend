from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domains.identity.exceptions import InvalidAccessToken
from app.domains.identity.security.jwt import JwtAccessTokenProvider


NOW = datetime(2026, 10, 27, 8, 30, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def build_provider(rsa_keys, *, clock):
    private_key, public_key = rsa_keys
    return JwtAccessTokenProvider(
        private_key=private_key,
        public_keys={"key-1": public_key},
        active_key_id="key-1",
        issuer="mnr-backend",
        audience="mnr-admin-web",
        access_token_ttl=timedelta(minutes=15),
        leeway=timedelta(0),
        clock=clock,
        token_id_factory=lambda: "jwt-token-id",
    )


def test_issue_and_decode_rs256_access_token(rsa_keys):
    provider = build_provider(rsa_keys, clock=lambda: NOW)

    issued = provider.issue_access_token(
        user_id="user-271026-12345678",
        session_id="sess-271026-12345678",
        role_id="role-12345678",
    )
    claims = provider.decode_access_token(issued.token)

    assert jwt.get_unverified_header(issued.token) == {
        "alg": "RS256",
        "kid": "key-1",
        "typ": "JWT",
    }
    assert claims.user_id == "user-271026-12345678"
    assert claims.session_id == "sess-271026-12345678"
    assert claims.role_id == "role-12345678"
    assert claims.token_id == "jwt-token-id"
    assert claims.expires_at == NOW + timedelta(minutes=15)
    assert issued.expires_at == claims.expires_at


def test_decode_rejects_expired_access_token(rsa_keys):
    current_time = [NOW]
    provider = build_provider(rsa_keys, clock=lambda: current_time[0])
    issued = provider.issue_access_token(
        user_id="user-271026-12345678",
        session_id="sess-271026-12345678",
        role_id="role-12345678",
    )
    current_time[0] = NOW + timedelta(minutes=16)

    with pytest.raises(InvalidAccessToken, match="expired"):
        provider.decode_access_token(issued.token)


def test_decode_rejects_wrong_audience_and_unknown_key(rsa_keys):
    private_key, public_key = rsa_keys
    provider = build_provider(rsa_keys, clock=lambda: NOW)
    common_payload = {
        "iss": "mnr-backend",
        "aud": "another-client",
        "sub": "user-271026-12345678",
        "sid": "sess-271026-12345678",
        "role_id": "role-12345678",
        "type": "access",
        "jti": "jwt-token-id",
        "iat": int(NOW.timestamp()),
        "nbf": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(minutes=15)).timestamp()),
    }
    wrong_audience_token = jwt.encode(
        common_payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "key-1"},
    )
    unknown_key_token = jwt.encode(
        {**common_payload, "aud": "mnr-admin-web"},
        private_key,
        algorithm="RS256",
        headers={"kid": "unknown-key"},
    )

    with pytest.raises(InvalidAccessToken):
        provider.decode_access_token(wrong_audience_token)
    with pytest.raises(InvalidAccessToken, match="not recognized"):
        provider.decode_access_token(unknown_key_token)

    assert public_key in provider.public_keys.values()


def test_constructor_requires_active_public_key(rsa_keys):
    private_key, _public_key = rsa_keys

    with pytest.raises(ValueError, match="active_key_id"):
        JwtAccessTokenProvider(
            private_key=private_key,
            public_keys={},
            active_key_id="missing-key",
            issuer="mnr-backend",
            audience="mnr-admin-web",
        )
