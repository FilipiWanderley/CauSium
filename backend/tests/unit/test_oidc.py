"""
Unit tests for OIDC Azure — no database required.

Covers _verify_azure_id_token (static, pure) and _fetch_azure_jwks (cache logic).
The full route-level callback tests live in tests/integration/test_oidc_azure.py
and require a running PostgreSQL.
"""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from jose import jwt as jose_jwt

from app.domains.auth.service import AuthService


# ---------------------------------------------------------------------------
# RSA key helpers — generated once per module
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

    return {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "alg": "RS256",
        "n": _b64url(pub.n),
        "e": _b64url(pub.e),
    }


def _make_jwks(kid: str = "test-key-id") -> dict:
    return {"keys": [_jwk_from_public_key(kid)]}


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
    pk = private_key or _PRIVATE_KEY
    pem = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    now = int(time.time())
    claims: dict = {
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
# build_azure_oidc_start_url
# ---------------------------------------------------------------------------

class TestBuildAzureOidcStartUrl:
    def _fake_settings(self):
        s = MagicMock()
        s.azure_client_id = "fake-client-id"
        s.azure_tenant_id = "fake-tenant"
        s.azure_oidc_redirect_uri = "http://localhost/callback"
        s.azure_oidc_scopes = "openid profile email"
        s.secret_key = "test-secret-key-for-tests-at-least-32-chars"
        return s

    def test_raises_when_client_id_empty(self):
        s = self._fake_settings()
        s.azure_client_id = ""
        with patch("app.domains.auth.service.get_settings", return_value=s):
            svc = AuthService.__new__(AuthService)
            with pytest.raises(ValueError, match="azure_client_id is empty"):
                svc.build_azure_oidc_start_url()

    def test_url_contains_nonce_param(self):
        with patch("app.domains.auth.service.get_settings", return_value=self._fake_settings()):
            svc = AuthService.__new__(AuthService)
            url = svc.build_azure_oidc_start_url()
        assert "nonce=" in url

    def test_url_contains_state_param(self):
        with patch("app.domains.auth.service.get_settings", return_value=self._fake_settings()):
            svc = AuthService.__new__(AuthService)
            url = svc.build_azure_oidc_start_url()
        assert "state=" in url

    def test_nonce_in_url_matches_nonce_in_state(self):
        """The nonce embedded in the state JWT must equal the nonce URL param."""
        from urllib.parse import parse_qs, urlsplit
        import app.domains.auth.service as svc_module  # noqa: F401

        secret = "test-secret-key-for-tests-at-least-32-chars"
        s = self._fake_settings()
        s.secret_key = secret
        with patch("app.domains.auth.service.get_settings", return_value=s):
            svc = AuthService.__new__(AuthService)
            url = svc.build_azure_oidc_start_url()

        qs = parse_qs(urlsplit(url).query)
        url_nonce = qs["nonce"][0]
        state_token = qs["state"][0]
        state_claims = jose_jwt.decode(state_token, secret, algorithms=["HS256"])
        assert state_claims["nonce"] == url_nonce


# ---------------------------------------------------------------------------
# _verify_azure_id_token  (static, no network, no DB)
# ---------------------------------------------------------------------------

class TestVerifyAzureIdToken:
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
        claims = self._call(_make_id_token())
        assert claims["preferred_username"] == "user@example.com"

    def test_unsupported_hs256_algorithm_rejected(self):
        hs_token = jose_jwt.encode(
            {"sub": "x", "exp": int(time.time()) + 3600}, "secret", algorithm="HS256"
        )
        with pytest.raises(ValueError, match="Unsupported id_token algorithm"):
            self._call(hs_token)

    def test_unknown_kid_raises(self):
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

    def test_wrong_issuer_multi_tenant_non_azure_domain_rejected(self):
        token = _make_id_token(iss="https://evil.example.com/v2.0")
        with pytest.raises(ValueError, match="not a valid Azure AD v2 URL"):
            AuthService._verify_azure_id_token(
                token,
                jwks=self._JWKS,
                nonce="test-nonce",
                tenant="common",
                client_id="test-client-id",
            )

    def test_valid_multi_tenant_guid_issuer_accepted(self):
        guid = "11111111-1111-1111-1111-111111111111"
        token = _make_id_token(iss=f"https://login.microsoftonline.com/{guid}/v2.0")
        claims = AuthService._verify_azure_id_token(
            token,
            jwks=self._JWKS,
            nonce="test-nonce",
            tenant="common",
            client_id="test-client-id",
        )
        assert claims["sub"] == "oid-abc123"

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

        other_key = rsa.generate_private_key(65537, 2048, default_backend())
        token = _make_id_token(private_key=other_key)
        with pytest.raises(ValueError, match="verification failed|signature"):
            self._call(token)

    def test_malformed_header_raises(self):
        with pytest.raises(ValueError, match="Cannot parse id_token header"):
            self._call("not.a.valid.jwt.here")


# ---------------------------------------------------------------------------
# _fetch_azure_jwks — caching behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFetchAzureJwksCache:
    async def _mock_client(self, jwks: dict, status: int = 200) -> MagicMock:
        mock_resp = _make_httpx_response(status, jwks)
        mock = MagicMock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock(return_value=False)
        mock.get = AsyncMock(return_value=mock_resp)
        return mock

    async def test_returns_jwks_on_success(self):
        jwks = _make_jwks()
        mock = await self._mock_client(jwks)
        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock):
            result = await AuthService._fetch_azure_jwks("tenant", ttl=300)
        assert result["keys"][0]["kid"] == "test-key-id"

    async def test_caches_within_ttl(self):
        jwks = _make_jwks()
        mock = await self._mock_client(jwks)
        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock):
            await AuthService._fetch_azure_jwks("tenant", ttl=300)
            await AuthService._fetch_azure_jwks("tenant", ttl=300)
        # Only one real HTTP call should have been made
        assert mock.get.call_count == 1

    async def test_refetches_after_expired_ttl(self):
        jwks = _make_jwks()
        mock = await self._mock_client(jwks)
        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock):
            await AuthService._fetch_azure_jwks("tenant", ttl=0)
            await AuthService._fetch_azure_jwks("tenant", ttl=0)
        assert mock.get.call_count == 2

    async def test_raises_on_http_error(self):
        mock = await self._mock_client({}, status=503)
        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock):
            with pytest.raises(ValueError, match="Failed to fetch Azure JWKS"):
                await AuthService._fetch_azure_jwks("tenant", ttl=300)

    async def test_raises_on_malformed_jwks(self):
        mock = await self._mock_client({"not_keys": []})
        with patch("app.domains.auth.service.httpx.AsyncClient", return_value=mock):
            with pytest.raises(ValueError, match="malformed"):
                await AuthService._fetch_azure_jwks("tenant", ttl=300)
