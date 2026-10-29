from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domains.identity.exceptions import InvalidAccessToken
from app.domains.identity.security import (
    Argon2PasswordHasher,
    JwtAccessTokenSigner,
    SecureRefreshTokenManager,
)


NOW = datetime(2026, 10, 26, 8, 30, tzinfo=timezone.utc)
USER_ID = "user-261026-12345678"
SESSION_ID = "sess-261026-12345678"


def test_argon2_password_hasher_hashes_and_verifies_plaintext():
    password_hasher = Argon2PasswordHasher()

    encoded_hash = password_hasher.hash_password("correct-password")

    assert encoded_hash.startswith("$argon2id$")
    assert encoded_hash != "correct-password"
    assert password_hasher.verify_password("correct-password", encoded_hash)
    assert not password_hasher.verify_password("wrong-password", encoded_hash)
    assert not password_hasher.verify_password("correct-password", None)


@pytest.mark.parametrize(
    "password",
    [
        " leading-space",
        "trailing-space ",
        "two words",
        "tab\tpassword",
        "line\nbreak",
        "unicode\u00a0space",
    ],
)
def test_argon2_password_hasher_rejects_whitespace(password: str):
    password_hasher = Argon2PasswordHasher()
    valid_hash = password_hasher.hash_password("valid-password")

    with pytest.raises(ValueError, match="must not contain whitespace"):
        password_hasher.hash_password(password)

    assert not password_hasher.verify_password(password, valid_hash)


def test_refresh_token_manager_only_persists_sha256_hash():
    manager = SecureRefreshTokenManager(
        token_factory=lambda token_bytes: f"refresh-token-{token_bytes}"
    )

    issued = manager.issue_refresh_token()

    assert issued.token == "refresh-token-48"
    assert len(issued.token_hash) == 64
    assert issued.token not in repr(issued)
    assert manager.hash_refresh_token(issued.token) == issued.token_hash


def test_jwt_signer_issues_and_verifies_rs256_access_token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    signer = JwtAccessTokenSigner(
        private_key=private_pem,
        public_keys={"key-1": public_pem},
        active_key_id="key-1",
        issuer="mnr-backend",
        audience="mnr-admin-web",
        access_token_ttl=timedelta(minutes=15),
        leeway=timedelta(0),
        clock=lambda: NOW,
        token_id_factory=lambda: "token-id-12345678",
    )

    issued_token = signer.issue_access_token(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-12345678",
    )
    claims = signer.decode_access_token(issued_token.token)

    assert issued_token.expires_at == NOW + timedelta(minutes=15)
    assert claims.user_id == USER_ID
    assert claims.session_id == SESSION_ID
    assert claims.role_id == "role-12345678"
    assert claims.token_id == "token-id-12345678"
    assert claims.expires_at == issued_token.expires_at

    # Thay đổi chỉ một ký tự cũng làm chữ ký không còn hợp lệ.
    with pytest.raises(InvalidAccessToken):
        signer.decode_access_token(f"{issued_token.token}x")
