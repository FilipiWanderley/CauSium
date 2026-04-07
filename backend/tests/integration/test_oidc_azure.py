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
        return _make_id_token(
            iss=f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            aud=self._CLIENT_ID, nonce=nonce, **kw,
        )

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

        async def _fetch(tenant, ttl):
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
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.core.config import get_settings
from app.domains.auth.service import AuthService, _JWKS_CACHE


# ---------------------------------------------------------------------------
# RSA key helpers — generated once per session for all tests
# ---------------------------------------------------------------------------

def _generate_rsa_keypair():
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    return private_key, private_key.public_key()


# Module-level key pair — reused across all tests in this module.
_PRIVATE_KEY, _PUBLIC_KEY = _generate_rsa_keypair()


def _jwk_from_public_key(kid: str = "test-key-id") -> dict:
    """Convert an RSA public key to a JWK dict that python-jose can use."""
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    import base64

    pub_numbers = _PUBLIC_KEY.public_numbers()

    def _b64url(n: int) -> str:
        byte_len = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).decode().rstrip("=")

    return {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "alg": "RS256",
        "n": _b64url(pub_numbers.n),
        "e": _b64url(pub_numbers.e),
    }


def _make_id_token(
    *,
    kid: str = "test-key-id",
    alg: str = "RS256",
    aud: str = "test-client-id",
    iss: str = "https://login.microsoftonline.com/test-tenant/v2.0",
    nonce: str = "test-nonce",
    email: str = "user@example.com",
    exp_offset_s: int = 3600,
    extra_claims: dict | None = None,
    private_key=None,
) -> str:
    """Build a signed RS256 id_token using our test RSA private key."""
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

    pk = private_key or _PRIVATE_KEY
    pem = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "sub": "oid-abc123",
        "preferred_username": email,
        "name": "Test User",
        "nonce": nonce,
        "iat": now,
        "nbf": now,
        "exp": now + exp_offset_s,
    }
    if extra_claims:
        claims.update(extra_claims)

    return jose_jwt.encode(claims, pem, algorithm=alg, headers={"kid": kid})


def _make_jwks(kid: str = "test-key-id") -> dict:
    return {"keys": [_jwk_from_public_key(kid)]}


def _make_state(
    *,
    secret: str = "test-secret-key-for-tests-at-least-32-chars",
    nonce: str = "test-nonce",
    provider: str = "azure",
    state_type: str = "oidc_state",
    exp_offset_minutes: int = 10,
) -> str:
    payload = {
        "type": state_type,
        "provider": provider,
        "nonce": nonce,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_offset_minutes),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_httpx_response(status_code: int, body: dict) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = body
    mock.text = json.dumps(body)
    return mock


def _mock_token_exchange(id_token: str):
    """Return an AsyncClient mock that yields a valid token exchange response."""
    async def _fake_post(*args, **kwargs):
        return _make_httpx_response(200, {"id_token": id_token, "access_token": "at", "token_type": "Bearer"})

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = _fake_post
    return mock_client


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    """Reset the module-level JWKS cache before every test."""
    import app.domains.auth.service as svc_module
    svc_module._JWKS_CACHE = {"data": None, "fetched_at": 0.0}
    yield
    svc_module._JWKS_CACHE = {"data": None, "fetched_at": 0.0}


# ---------------------------------------------------------------------------
# Tests: build_azure_oidc_start_url
# ---------------------------------------------------------------------------

class TestBuildAzureOidcStartUrl:
    def test_raises_when_client_id_empty(self, db):
        with patch("app.domains.auth.service.get_settings") as mock_settings:
            s = MagicMock()
            s.azure_client_id = ""
            mock_settings.return_value = s
            svc = AuthService.__new__(AuthService)
            with pytest.raises(ValueError, match="azure_client_id is empty"):
                svc.build_azure_oidc_start_url()

    def test_url_contains_nonce_param(self, db):
        settings = get_settings()
        if not settings.azure_client_id:
            # Inject a fake client_id so we can test URL generation without real Azure creds
            with patch("app.domains.auth.service.get_settings") as mock_settings:
                s = MagicMock()
                s.azure_client_id = "fake-client-id"
                s.azure_tenant_id = "fake-tenant"
                s.azure_oidc_redirect_uri = "http://localhost/callback"
                s.azure_oidc_scopes = "openid profile email"
                s.secret_key = "test-secret-key-for-tests-at-least-32-chars"
                mock_settings.return_value = s
                svc = AuthService.__new__(AuthService)
                url = svc.build_azure_oidc_start_url()
        assert "nonce=" in url

    def test_url_contains_state_param(self, db):
        with patch("app.domains.auth.service.get_settings") as mock_settings:
            s = MagicMock()
            s.azure_client_id = "fake-client-id"
            s.azure_tenant_id = "fake-tenant"
            s.azure_oidc_redirect_uri = "http://localhost/callback"
            s.azure_oidc_scopes = "openid profile email"
            s.secret_key = "test-secret-key-for-tests-at-least-32-chars"
            mock_settings.return_value = s
            svc = AuthService.__new__(AuthService)
            url = svc.build_azure_oidc_start_url()
        assert "state=" in url


# ---------------------------------------------------------------------------
# Tests: _verify_azure_id_token (unit — no HTTP, no DB)
# ---------------------------------------------------------------------------

class TestVerifyAzureIdToken:
    """Direct unit tests for the static id_token verifier."""

    _JWKS = _make_jwks()

    def _call(self, id_token: str, **overrides) -> dict:
        kwargs = dict(
            jwks=self._JWKS,
            nonce="test-nonce",
            tenant="test-tenant",
            client_id="test-client-id",
        )
        kwargs.update(overrides)
        return AuthService._verify_azure_id_token(id_token, **kwargs)

    def test_valid_token_returns_claims(self):
        token = _make_id_token()
        claims = self._call(token)
        assert claims["preferred_username"] == "user@example.com"

    def test_unsupported_algorithm_rejected(self):
        with pytest.raises(ValueError, match="Unsupported id_token algorithm"):
            AuthService._verify_azure_id_token(
                "header.payload.sig",
                jwks=self._JWKS,
                nonce="n",
                tenant="t",
                client_id="c",
            )
        # Build a token with HS256 (symmetric — should be rejected)
        hs_token = jose_jwt.encode({"sub": "x", "exp": int(time.time()) + 3600}, "secret", algorithm="HS256")
        with pytest.raises(ValueError, match="Unsupported id_token algorithm"):
            self._call(hs_token)

    def test_wrong_kid_raises(self):
        token = _make_id_token(kid="unknown-kid")
        with pytest.raises(ValueError, match="No JWKS key found for kid"):
            self._call(token)

    def test_wrong_audience_raises(self):
        token = _make_id_token(aud="wrong-client-id")
        with pytest.raises(ValueError, match="claims invalid|verification failed"):
            self._call(token)

    def test_wrong_issuer_single_tenant_raises(self):
        token = _make_id_token(iss="https://login.microsoftonline.com/other-tenant/v2.0")
        with pytest.raises(ValueError, match="issuer mismatch"):
            self._call(token)

    def test_wrong_issuer_multi_tenant_rejects_non_azure_url(self):
        token = _make_id_token(iss="https://evil.example.com/v2.0")
        with pytest.raises(ValueError, match="not a valid Azure AD v2 URL"):
            AuthService._verify_azure_id_token(
                token,
                jwks=self._JWKS,
                nonce="test-nonce",
                tenant="common",
                client_id="test-client-id",
            )

    def test_valid_multi_tenant_issuer_accepted(self):
        some_tenant_guid = "11111111-1111-1111-1111-111111111111"
        token = _make_id_token(iss=f"https://login.microsoftonline.com/{some_tenant_guid}/v2.0")
        claims = AuthService._verify_azure_id_token(
            token,
            jwks=self._JWKS,
            nonce="test-nonce",
            tenant="common",
            client_id="test-client-id",
        )
        assert claims["preferred_username"] == "user@example.com"

    def test_nonce_mismatch_raises(self):
        token = _make_id_token(nonce="correct-nonce")
        with pytest.raises(ValueError, match="nonce mismatch"):
            self._call(token, nonce="wrong-nonce")

    def test_expired_token_raises(self):
        token = _make_id_token(exp_offset_s=-1)
        with pytest.raises(ValueError, match="expired"):
            self._call(token)

    def test_wrong_signature_raises(self):
        from cryptography.hazmat.backends import default_backend

        other_private = rsa.generate_private_key(65537, 2048, default_backend())
        # Sign with a different key but keep the same kid in the JWKS (verification key mismatch)
        token = _make_id_token(private_key=other_private)
        with pytest.raises(ValueError, match="verification failed|signature"):
            self._call(token)


# ---------------------------------------------------------------------------
# Tests: _fetch_azure_jwks caching
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFetchAzureJwksCache:
    async def test_caches_within_ttl(self):
        jwks = _make_jwks()
        fetch_count = 0

        async def _fake_get(url):
            nonlocal fetch_count
            fetch_count += 1
            return _make_httpx_response(200, jwks)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = _fake_get

        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock_client):
            # First call — should hit network
            result1 = await AuthService._fetch_azure_jwks("tenant", ttl=300)
            # Second call within TTL — should return cached copy
            result2 = await AuthService._fetch_azure_jwks("tenant", ttl=300)

        assert fetch_count == 1
        assert result1 == result2

    async def test_refetches_after_ttl(self):
        jwks = _make_jwks()
        fetch_count = 0

        async def _fake_get(url):
            nonlocal fetch_count
            fetch_count += 1
            return _make_httpx_response(200, jwks)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = _fake_get

        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock_client):
            await AuthService._fetch_azure_jwks("tenant", ttl=0)  # TTL=0 → always stale
            await AuthService._fetch_azure_jwks("tenant", ttl=0)

        assert fetch_count == 2

    async def test_raises_on_http_error(self):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            return_value=_make_httpx_response(500, {"error": "server error"})
        )

        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Failed to fetch Azure JWKS"):
                await AuthService._fetch_azure_jwks("tenant", ttl=300)


# ---------------------------------------------------------------------------
# Tests: full OIDC callback route (via FastAPI test client)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAzureOidcCallback:
    """End-to-end tests for GET /api/v1/auth/oidc/azure/callback via the HTTP client."""

    _JWKS = _make_jwks()
    _SETTINGS_SECRET = "test-secret-key-for-tests-at-least-32-chars"
    _CLIENT_ID = "test-client-id"
    _TENANT = "test-tenant"

    def _state(self, nonce: str = "test-nonce", **overrides) -> str:
        return _make_state(secret=self._SETTINGS_SECRET, nonce=nonce, **overrides)

    def _id_token(self, nonce: str = "test-nonce", **overrides) -> str:
        return _make_id_token(
            iss=f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            aud=self._CLIENT_ID,
            nonce=nonce,
            **overrides,
        )

    def _patch_settings(self):
        """Context manager that injects fake Azure settings."""
        from unittest.mock import patch

        real_settings = get_settings()

        class _FakeSettings:
            secret_key = self._SETTINGS_SECRET
            azure_client_id = self._CLIENT_ID
            azure_client_secret = "fake-secret"
            azure_tenant_id = self._TENANT
            azure_oidc_redirect_uri = "http://localhost/callback"
            azure_oidc_scopes = "openid profile email"
            oidc_jwks_cache_ttl_seconds = 300
            frontend_url = real_settings.frontend_url
            auth_cookie_access_name = real_settings.auth_cookie_access_name
            auth_cookie_refresh_name = real_settings.auth_cookie_refresh_name
            auth_cookie_domain = real_settings.auth_cookie_domain
            auth_cookie_path = real_settings.auth_cookie_path
            auth_cookie_samesite = real_settings.auth_cookie_samesite
            auth_cookie_secure = None
            is_production = False
            auth_cookie_secure_effective = False

        return patch("app.domains.auth.service.get_settings", return_value=_FakeSettings())

    def _patch_token_exchange(self, id_token: str, status_code: int = 200):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        if status_code >= 400:
            mock_client.post = AsyncMock(
                return_value=_make_httpx_response(status_code, {"error": "bad_request"})
            )
        else:
            mock_client.post = AsyncMock(
                return_value=_make_httpx_response(200, {"id_token": id_token})
            )
        return mock_client

    def _patch_jwks(self, jwks: dict | None = None):
        _jwks = jwks or self._JWKS

        async def _fetch(tenant, ttl):
            return _jwks

        return patch.object(AuthService, "_fetch_azure_jwks", _fetch)

    async def _callback(self, client, code: str = "valid-code", state: str | None = None) -> Any:
        s = state or self._state()
        return await client.get(
            f"/api/v1/auth/oidc/azure/callback?code={code}&state={s}",
            follow_redirects=False,
        )

    async def test_successful_callback_redirects_to_dashboard(self, client):
        id_token = self._id_token()
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" not in resp.headers["location"]

    async def test_invalid_state_signature_causes_error_redirect(self, client):
        state = _make_state(secret="wrong-secret-key-thats-at-least-32-chars")
        resp = await client.get(
            f"/api/v1/auth/oidc/azure/callback?code=abc&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_expired_state_causes_error_redirect(self, client):
        state = _make_state(exp_offset_minutes=-1)
        resp = await client.get(
            f"/api/v1/auth/oidc/azure/callback?code=abc&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_token_exchange_http_error_causes_error_redirect(self, client):
        id_token = self._id_token()
        token_mock = self._patch_token_exchange(id_token, status_code=400)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_missing_id_token_causes_error_redirect(self, client):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            return_value=_make_httpx_response(200, {"access_token": "at"})  # no id_token
        )

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock_client), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_signature_causes_error_redirect(self, client):
        from cryptography.hazmat.backends import default_backend

        other_key = rsa.generate_private_key(65537, 2048, default_backend())
        id_token = _make_id_token(
            private_key=other_key,
            nonce="test-nonce",
            iss=f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            aud=self._CLIENT_ID,
        )
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_nonce_mismatch_causes_error_redirect(self, client):
        state = self._state(nonce="state-nonce")
        id_token = self._id_token(nonce="different-nonce")
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await client.get(
                f"/api/v1/auth/oidc/azure/callback?code=abc&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_aud_causes_error_redirect(self, client):
        id_token = self._id_token(aud="wrong-client-id")
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_id_token_wrong_iss_causes_error_redirect(self, client):
        id_token = self._id_token(iss="https://evil.example.com/v2.0")
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_expired_id_token_causes_error_redirect(self, client):
        id_token = self._id_token(exp_offset_s=-1)
        token_mock = self._patch_token_exchange(id_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

    async def test_missing_email_claim_causes_error_redirect(self, client):
        id_token = _make_id_token(
            iss=f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
            aud=self._CLIENT_ID,
            nonce="test-nonce",
            extra_claims={"preferred_username": None},
        )
        # Override with no email fields at all
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
        pem = _PRIVATE_KEY.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        now = int(time.time())
        no_email_token = jose_jwt.encode(
            {
                "iss": f"https://login.microsoftonline.com/{self._TENANT}/v2.0",
                "aud": self._CLIENT_ID,
                "sub": "uid",
                "nonce": "test-nonce",
                "iat": now,
                "exp": now + 3600,
                # deliberately omitting preferred_username, email, upn
            },
            pem,
            algorithm="RS256",
            headers={"kid": "test-key-id"},
        )
        token_mock = self._patch_token_exchange(no_email_token)

        with self._patch_settings(), \
             patch("app.domains.auth.service.httpx.AsyncClient", return_value=token_mock), \
             self._patch_jwks():
            resp = await self._callback(client)

        assert resp.status_code == 307
        assert "oidc_error" in resp.headers["location"]

