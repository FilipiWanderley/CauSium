"""
Integration tests for SP-A: Azure OIDC secure callback route.

Tests the full GET /api/v1/auth/oidc/azure/callback path through the FastAPI
application, requiring a live PostgreSQL database (managed by conftest.py).

Pure unit tests for _verify_azure_id_token, _fetch_azure_jwks, and
build_azure_oidc_start_url live in tests/unit/test_oidc.py.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from jose import jwt as jose_jwt

from app.core.config import get_settings
from app.domains.auth.service import AuthService


# ---------------------------------------------------------------------------
# Shared RSA key pair for this module
# ---------------------------------------------------------------------------

def _generate_rsa_keypair():
    from cryptography.hazmat.backends import default_backend

    pk = rsa.generate_private_key(65537, 2048, backend=default_backend())
    return pk, pk.public_key()


_PRIVATE_KEY, _PUBLIC_KEY = _generate_rsa_keypair()


def _jwk_from_public_key(kid: str = "test-key-id") -> dict:
    import base64

    pub = _PUBLIC_KEY.public_numbers()

    def _b64url(n: int) -> str:
        byte_len = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).decode().rstrip("=")

    return {"kty": "RSA", "use": "sig", "kid": kid, "alg": "RS256",
            "n": _b64url(pub.n), "e": _b64url(pub.e)}


def _make_jwks(kid: str = "test-key-id") -> dict:
    return {"keys": [_jwk_from_public_key(kid)]}


def _make_id_token(
    *,
    kid: str = "test-key-id",
    aud: str = "test-client-id",
    iss: str = "https://login.microsoftonline.com/test-tenant/v2.0",
    nonce: str = "test-nonce",
    email: str = "oidc@example.com",
    exp_offset_s: int = 3600,
    extra_claims: dict | None = None,
    private_key=None,
) -> str:
    pk = private_key or _PRIVATE_KEY
    pem = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": iss, "aud": aud, "sub": "oid-xyz",
        "preferred_username": email, "name": "OIDC User",
        "nonce": nonce, "iat": now, "nbf": now, "exp": now + exp_offset_s,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jose_jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def _make_state(
    *,
    secret: str = "test-secret-key-for-tests-at-least-32-chars",
    nonce: str = "test-nonce",
    exp_offset_minutes: int = 10,
) -> str:
    payload = {
        "type": "oidc_state", "provider": "azure", "nonce": nonce,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_offset_minutes),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _make_httpx_response(status_code: int, body: dict) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = body
    m.text = json.dumps(body)
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    import app.domains.auth.service as svc_module

    svc_module._JWKS_CACHE = {"data": None, "fetched_at": 0.0}
    yield
    svc_module._JWKS_CACHE = {"data": None, "fetched_at": 0.0}


# ---------------------------------------------------------------------------
# Route-level tests (require DB + FastAPI test client)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAzureOidcCallbackRoute:
    _JWKS = _make_jwks()
    _SECRET = "test-secret-key-for-tests-at-least-32-chars"
    _CLIENT_ID = "test-client-id"
    _TENANT = "test-tenant"

    def _state(self, nonce: str = "test-nonce", **kw) -> str:
        return _make_state(secret=self._SECRET, nonce=nonce, **kw)

    def _id_token(self, nonce: str = "test-nonce", **kw) -> str:
        payload = {
            "iss": f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            "aud": self._CLIENT_ID,
            "nonce": nonce,
        }
        payload.update(kw)
        return _make_id_token(**payload)

    def _patch_settings(self):
        real = get_settings()

        class _Fake:
            secret_key = self._SECRET
            azure_client_id = self._CLIENT_ID
            azure_client_secret = "fake-secret"
            azure_tenant_id = self._TENANT
            azure_oidc_redirect_uri = "http://localhost/callback"
            azure_oidc_scopes = "openid profile email"
            oidc_jwks_cache_ttl_seconds = 300
            frontend_url = real.frontend_url
            auth_cookie_access_name = real.auth_cookie_access_name
            auth_cookie_refresh_name = real.auth_cookie_refresh_name
            auth_cookie_domain = real.auth_cookie_domain
            auth_cookie_path = real.auth_cookie_path
            auth_cookie_samesite = real.auth_cookie_samesite
            auth_cookie_secure = None
            is_production = False
            auth_cookie_secure_effective = False

        return patch("app.domains.auth.service.get_settings", return_value=_Fake())

    def _patch_token_exchange(self, id_token: str | None, status: int = 200):
        mock = MagicMock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock(return_value=False)
        body = ({"id_token": id_token} if id_token else {"access_token": "at"}) if status < 400 else {"error": "bad"}
        mock.post = AsyncMock(return_value=_make_httpx_response(status, body))
        return mock

    def _patch_jwks(self, jwks: dict | None = None):
        _j = jwks or self._JWKS

        async def _fetch(_self, tenant, ttl):
            return _j

        return patch.object(AuthService, "_fetch_azure_jwks", _fetch)

    async def _get_callback(self, client, state: str | None = None) -> Any:
        s = state or self._state()
        return await client.get(
            f"/api/v1/auth/oidc/azure/callback?code=code&state={s}",
            follow_redirects=False,
        )

    # Happy path
    async def test_successful_login_redirects_without_error(self, client):
        id_token = self._id_token()
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" not in resp.headers["location"]

    # Negative paths — each must redirect with oidc_error in the URL
    async def test_invalid_state_signature(self, client):
        state = _make_state(secret="wrong-secret-key-thats-at-least-32-chars")
        resp = await client.get(
            f"/api/v1/auth/oidc/azure/callback?code=x&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_expired_state(self, client):
        state = self._state(exp_offset_minutes=-1)
        resp = await client.get(
            f"/api/v1/auth/oidc/azure/callback?code=x&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_token_exchange_error(self, client):
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(None, status=400)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_missing_id_token(self, client):
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(None, status=200)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_signature(self, client):
        from cryptography.hazmat.backends import default_backend

        other = rsa.generate_private_key(65537, 2048, default_backend())
        id_token = _make_id_token(
            private_key=other, nonce="test-nonce",
            iss=f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            aud=self._CLIENT_ID,
        )
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_nonce_mismatch(self, client):
        state = self._state(nonce="state-nonce")
        id_token = self._id_token(nonce="different-nonce")
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await client.get(
                f"/api/v1/auth/oidc/azure/callback?code=x&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_aud(self, client):
        id_token = self._id_token(aud="wrong-client-id")
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_iss(self, client):
        id_token = self._id_token(iss="https://evil.example.com/v2.0")
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_expired_id_token(self, client):
        id_token = self._id_token(exp_offset_s=-1)
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(id_token)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_missing_email_claim(self, client):
        pem = _PRIVATE_KEY.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        now = int(time.time())
        no_email = jose_jwt.encode(
            {
                "iss": f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
                "aud": self._CLIENT_ID, "sub": "uid", "nonce": "test-nonce",
                "iat": now, "exp": now + 3600,
            },
            pem, algorithm="RS256", headers={"kid": "test-key-id"},
        )
        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient",
                   return_value=self._patch_token_exchange(no_email)), \
             self._patch_jwks():
            resp = await self._get_callback(client)
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]
