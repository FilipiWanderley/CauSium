import base64
import json
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def _cbor_encode(value) -> bytes:
    def enc_len(major: int, n: int) -> bytes:
        if n < 24:
            return bytes([(major << 5) | n])
        if n < 256:
            return bytes([(major << 5) | 24, n])
        if n < 65536:
            return bytes([(major << 5) | 25]) + n.to_bytes(2, "big")
        return bytes([(major << 5) | 26]) + n.to_bytes(4, "big")

    if isinstance(value, bool):
        return b"\xf5" if value else b"\xf4"
    if value is None:
        return b"\xf6"
    if isinstance(value, int):
        if value >= 0:
            return enc_len(0, value)
        return enc_len(1, -1 - value)
    if isinstance(value, bytes):
        return enc_len(2, len(value)) + value
    if isinstance(value, str):
        raw = value.encode()
        return enc_len(3, len(raw)) + raw
    if isinstance(value, list):
        return enc_len(4, len(value)) + b"".join(_cbor_encode(v) for v in value)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(_cbor_encode(k))
            parts.append(_cbor_encode(v))
        return enc_len(5, len(value)) + b"".join(parts)
    raise TypeError("Unsupported CBOR value")


@pytest.mark.asyncio
async def test_passkey_registration_and_login_flow(client, auth_headers):
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    email = me.json()["email"]
    assert me.json()["passkey_enabled"] is False

    opts = await client.post(
        "/api/v1/auth/passkey/register/options",
        json={"display_name": "Demo User"},
        headers=auth_headers,
    )
    assert opts.status_code == 200, opts.text
    reg_challenge = opts.json()["challenge"]

    client_data_create = _b64url(
        json.dumps(
            {
                "type": "webauthn.create",
                "challenge": reg_challenge,
                "origin": "http://localhost:5173",
            }
        ).encode()
    )
    credential_id = _b64url(b"credential-demo-1")
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, "big")
    y = public_numbers.y.to_bytes(32, "big")
    public_key_jwk = {"kty": "EC", "crv": "P-256", "x": _b64url(x), "y": _b64url(y)}
    credential_id_raw = _b64url_decode(credential_id)
    registration_authenticator_data = (
        sha256(b"localhost").digest()
        + bytes([0x41])
        + (1).to_bytes(4, byteorder="big")
        + (b"\x00" * 16)
        + len(credential_id_raw).to_bytes(2, byteorder="big")
        + credential_id_raw
        + b"\xA5\x01\x02"
    )
    attestation_object = _cbor_encode(
        {
            "fmt": "none",
            "authData": registration_authenticator_data,
            "attStmt": {},
        }
    )

    verify_reg = await client.post(
        "/api/v1/auth/passkey/register/verify",
        json={
            "challenge": reg_challenge,
            "credential_id": credential_id,
            "public_key_jwk": public_key_jwk,
            "client_data_json": client_data_create,
            "authenticator_data": _b64url(registration_authenticator_data),
            "attestation_object": _b64url(attestation_object),
            "transports": ["internal"],
            "sign_count": 1,
        },
        headers=auth_headers,
    )
    assert verify_reg.status_code == 204, verify_reg.text

    me_after = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_after.status_code == 200
    assert me_after.json()["passkey_enabled"] is True

    listed = await client.get("/api/v1/auth/passkeys", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    passkey_id = listed.json()[0]["id"]

    login_opts = await client.post(
        "/api/v1/auth/passkey/login/options",
        json={"email": email},
    )
    assert login_opts.status_code == 200, login_opts.text
    login_challenge = login_opts.json()["challenge"]
    assert credential_id in login_opts.json()["allow_credentials"]

    client_data_get = _b64url(
        json.dumps(
            {
                "type": "webauthn.get",
                "challenge": login_challenge,
                "origin": "http://localhost:5173",
            }
        ).encode()
    )
    authenticator_data = sha256(b"localhost").digest() + bytes([0x01]) + (2).to_bytes(4, byteorder="big")
    signed_data = authenticator_data + sha256(_b64url_decode(client_data_get)).digest()
    signature = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))
    verify_login = await client.post(
        "/api/v1/auth/passkey/login/verify",
        json={
            "email": email,
            "challenge": login_challenge,
            "credential_id": credential_id,
            "client_data_json": client_data_get,
            "authenticator_data": _b64url(authenticator_data),
            "signature": _b64url(signature),
            "sign_count": 2,
        },
    )
    assert verify_login.status_code == 200, verify_login.text
    body = verify_login.json()
    assert "access_token" in body
    assert body["user"]["passkey_enabled"] is True

    revoked = await client.delete(f"/api/v1/auth/passkeys/{passkey_id}", headers=auth_headers)
    assert revoked.status_code == 204, revoked.text
    listed_after = await client.get("/api/v1/auth/passkeys", headers=auth_headers)
    assert listed_after.status_code == 200
    assert listed_after.json() == []
    me_after_revoke = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_after_revoke.status_code == 200
    assert me_after_revoke.json()["passkey_enabled"] is False

    reg_events = await client.get("/api/v1/audit-chain/events?event_type=auth.passkey.registered", headers=auth_headers)
    assert reg_events.status_code == 200, reg_events.text
    assert len(reg_events.json()) >= 1
    login_events = await client.get("/api/v1/audit-chain/events?event_type=auth.passkey.login", headers=auth_headers)
    assert login_events.status_code == 200, login_events.text
    assert len(login_events.json()) >= 1
    revoke_events = await client.get("/api/v1/audit-chain/events?event_type=auth.passkey.revoked", headers=auth_headers)
    assert revoke_events.status_code == 200, revoke_events.text
    assert len(revoke_events.json()) >= 1
    auth_feed = await client.get("/api/v1/audit-chain/events/auth", headers=auth_headers)
    assert auth_feed.status_code == 200, auth_feed.text
    assert len(auth_feed.json()) >= 3
    export = await client.get(
        "/api/v1/audit-chain/events/export/jsonl?event_prefix=auth.",
        headers=auth_headers,
    )
    assert export.status_code == 200, export.text
    assert export.headers["content-type"].startswith("application/x-ndjson")
    lines = [ln for ln in export.text.splitlines() if ln.strip()]
    assert len(lines) >= 3


@pytest.mark.asyncio
async def test_passwordless_only_blocks_password_login(client, auth_headers):
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    email = me.json()["email"]

    policy = await client.patch(
        "/api/v1/auth/passwordless-policy",
        json={"passwordless_only": True},
        headers=auth_headers,
    )
    assert policy.status_code == 200, policy.text
    assert policy.json()["passwordless_only"] is True

    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert blocked.status_code == 401
