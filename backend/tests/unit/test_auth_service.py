import pytest

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_hash_and_verify():
    password = "my_secure_password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip():
    token = create_access_token("user-123", {"org_id": "org-456", "role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["org_id"] == "org-456"
    assert payload["type"] == "access"


def test_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_token("invalid.token.here")


def test_token_has_expiry():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert "exp" in payload
