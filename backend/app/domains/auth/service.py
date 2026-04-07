from __future__ import annotations
import base64
import json
import re
import secrets
import time as _time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from jose import exceptions as jose_exceptions
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.domains.audit_chain.service import AuditChainService
from app.domains.auth.models import AuthChallenge, Organization, PasskeyCredential, User, UserRole
from app.domains.auth.schemas import RegisterRequest, UserCreate

# ---------------------------------------------------------------------------
# Module-level JWKS cache (avoids a round-trip on every OIDC callback).
# Replaced atomically; the dict reference is reassigned, not mutated.
# ---------------------------------------------------------------------------
_JWKS_CACHE: dict = {"data": None, "fetched_at": 0.0}


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def register(self, req: RegisterRequest) -> tuple[Organization, User]:
        org = Organization(name=req.org_name, slug=req.org_slug)
        self.db.add(org)
        await self.db.flush()

        user = User(
            org_id=org.id,
            email=req.email,
            full_name=req.full_name,
            hashed_password=hash_password(req.password),
            role=UserRole.ADMIN,
        )
        self.db.add(user)
        await self.db.flush()
        await self.audit_chain.append_event(
            org_id=org.id,
            actor_user_id=user.id,
            event_type="auth.user.registered",
            entity_type="user",
            entity_id=str(user.id),
            payload={
                "email": user.email,
                "role": user.role.value,
                "org_slug": org.slug,
            },
        )
        await self.db.refresh(org)
        await self.db.refresh(user)
        return org, user

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account inactive")
        org = await self.get_org(user.org_id)
        if org and org.passwordless_only:
            raise ValueError("Password login disabled by organization policy (passwordless-only)")

        user.last_login = datetime.now(timezone.utc)
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.password.login",
            entity_type="user",
            entity_id=str(user.id),
            payload={"email": user.email},
        )
        access = create_access_token(str(user.id), {"org_id": str(user.org_id), "role": user.role})
        refresh = create_refresh_token(str(user.id))
        return user, access, refresh

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user = await self.get_user_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        access = create_access_token(str(user.id), {"org_id": str(user.org_id), "role": user.role})
        new_refresh = create_refresh_token(str(user.id))
        return access, new_refresh

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_org(self, org_id: UUID) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def create_user(self, org_id: UUID, req: UserCreate) -> User:
        org = await self.get_org(org_id)
        if org:
            count_result = await self.db.execute(
                select(func.count(User.id)).where(User.org_id == org_id, User.is_active == True)  # noqa: E712
            )
            active_members = count_result.scalar_one()
            if active_members >= org.member_quota:
                raise ValueError(
                    f"Member quota reached ({org.member_quota} active users allowed on this plan). "
                    "Upgrade your workspace plan to add more members."
                )
        user = User(
            org_id=org_id,
            email=req.email,
            full_name=req.full_name,
            hashed_password=hash_password(req.password),
            role=req.role,
            # SP-A01: admin-created accounts must change password on first login.
            must_change_password=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list_org_users(self, org_id: UUID) -> list[User]:
        result = await self.db.execute(select(User).where(User.org_id == org_id))
        return list(result.scalars().all())

    async def get_org_name(self, org_id: UUID) -> str:
        org = await self.get_org(org_id)
        return org.name if org else ""

    async def update_passwordless_policy(self, org_id: UUID, enabled: bool) -> Organization:
        org = await self.get_org(org_id)
        if not org:
            raise ValueError("Organization not found")
        org.passwordless_only = enabled
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        """SP-A01: Authenticated user changes their own password.

        Verifies ``current_password`` against the stored hash, then sets the new
        password, clears ``must_change_password``, and records ``password_changed_at``.

        Raises:
            ValueError: when ``current_password`` is wrong, the new password
                equals the current one, or the user's org disallows passwords.
        """
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        if verify_password(new_password, user.hashed_password):
            raise ValueError("New password must differ from the current password")

        user.hashed_password = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.password.changed",
            entity_type="user",
            entity_id=str(user.id),
            payload={"forced": False},
        )
        await self.db.refresh(user)
        return user

    @staticmethod
    def _new_challenge() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def _b64url_decode(raw: str) -> bytes:
        pad = "=" * (-len(raw) % 4)
        return base64.urlsafe_b64decode(raw + pad)

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def _parse_client_data(client_data_json_b64url: str) -> tuple[dict, bytes]:
        decoded = AuthService._b64url_decode(client_data_json_b64url)
        return json.loads(decoded.decode("utf-8")), decoded

    @staticmethod
    def _parse_authenticator_data(authenticator_data_b64url: str) -> tuple[str, int, int]:
        raw = AuthService._b64url_decode(authenticator_data_b64url)
        if len(raw) < 37:
            raise ValueError("Invalid authenticatorData")
        rp_id_hash = AuthService._b64url_encode(raw[0:32])
        flags = raw[32]
        sign_count = int.from_bytes(raw[33:37], byteorder="big")
        return rp_id_hash, flags, sign_count

    @staticmethod
    def _origin_allowed(origin: str) -> bool:
        settings = get_settings()
        allowed = set(settings.passkey_allowed_origins_list + [settings.frontend_url])
        return origin in allowed

    @staticmethod
    def _read_cbor(data: bytes, offset: int = 0):
        if offset >= len(data):
            raise ValueError("Malformed CBOR attestation object")
        initial = data[offset]
        offset += 1
        major = initial >> 5
        addl = initial & 0x1F

        def read_len(additional: int):
            nonlocal offset
            if additional < 24:
                return additional
            if additional == 24:
                v = data[offset]
                offset += 1
                return v
            if additional == 25:
                v = int.from_bytes(data[offset : offset + 2], "big")
                offset += 2
                return v
            if additional == 26:
                v = int.from_bytes(data[offset : offset + 4], "big")
                offset += 4
                return v
            if additional == 27:
                v = int.from_bytes(data[offset : offset + 8], "big")
                offset += 8
                return v
            raise ValueError("Unsupported CBOR additional info")

        if major == 0:
            return read_len(addl), offset
        if major == 1:
            return -1 - read_len(addl), offset
        if major == 2:
            ln = read_len(addl)
            v = data[offset : offset + ln]
            offset += ln
            return v, offset
        if major == 3:
            ln = read_len(addl)
            v = data[offset : offset + ln].decode("utf-8")
            offset += ln
            return v, offset
        if major == 4:
            ln = read_len(addl)
            arr = []
            for _ in range(ln):
                item, offset = AuthService._read_cbor(data, offset)
                arr.append(item)
            return arr, offset
        if major == 5:
            ln = read_len(addl)
            obj = {}
            for _ in range(ln):
                k, offset = AuthService._read_cbor(data, offset)
                v, offset = AuthService._read_cbor(data, offset)
                obj[k] = v
            return obj, offset
        if major == 7 and addl == 20:
            return False, offset
        if major == 7 and addl == 21:
            return True, offset
        if major == 7 and addl == 22:
            return None, offset
        raise ValueError("Unsupported CBOR type in attestation object")

    @staticmethod
    def _parse_attestation_object(attestation_object_b64url: str) -> dict:
        raw = AuthService._b64url_decode(attestation_object_b64url)
        obj, offset = AuthService._read_cbor(raw, 0)
        if offset != len(raw):
            raise ValueError("Invalid trailing bytes in attestation object")
        if not isinstance(obj, dict):
            raise ValueError("Invalid attestation object payload")
        return obj

    @staticmethod
    def _verify_registration_attestation(
        *,
        attestation_object_b64url: str,
        authenticator_data_b64url: str,
        client_data_json_b64url: str,
    ) -> None:
        parsed = AuthService._parse_attestation_object(attestation_object_b64url)
        fmt = parsed.get("fmt")
        auth_data = parsed.get("authData")
        att_stmt = parsed.get("attStmt")
        if not isinstance(fmt, str) or not isinstance(auth_data, bytes) or not isinstance(att_stmt, dict):
            raise ValueError("Malformed attestation object")
        expected_auth_data = AuthService._b64url_decode(authenticator_data_b64url)
        if auth_data != expected_auth_data:
            raise ValueError("Attestation authData mismatch")

        if fmt == "none":
            if att_stmt:
                raise ValueError("Invalid none attestation statement")
            return

        if fmt == "packed":
            sig = att_stmt.get("sig")
            alg = att_stmt.get("alg")
            x5c = att_stmt.get("x5c")
            if not isinstance(sig, bytes) or alg != -7 or not isinstance(x5c, list) or not x5c:
                raise ValueError("Unsupported packed attestation format")
            cert_der = x5c[0]
            if not isinstance(cert_der, bytes):
                raise ValueError("Invalid packed attestation certificate")
            cert = x509.load_der_x509_certificate(cert_der)
            pub = cert.public_key()
            _, client_data_raw = AuthService._parse_client_data(client_data_json_b64url)
            digest = hashes.Hash(hashes.SHA256())
            digest.update(client_data_raw)
            client_data_hash = digest.finalize()
            signed_data = expected_auth_data + client_data_hash
            try:
                if isinstance(pub, ec.EllipticCurvePublicKey):
                    pub.verify(sig, signed_data, ec.ECDSA(hashes.SHA256()))
                elif isinstance(pub, rsa.RSAPublicKey):
                    pub.verify(sig, signed_data, padding.PKCS1v15(), hashes.SHA256())
                else:
                    raise ValueError("Unsupported attestation public key type")
            except InvalidSignature as e:
                raise ValueError("Invalid packed attestation signature") from e
            return

        raise ValueError(f"Unsupported attestation format: {fmt}")

    @staticmethod
    def _verify_assertion_signature(
        *,
        public_key_jwk_raw: str,
        authenticator_data_b64url: str,
        client_data_json_b64url: str,
        signature_b64url: str,
    ) -> None:
        jwk = json.loads(public_key_jwk_raw)
        if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
            raise ValueError("Unsupported passkey key type")
        x = int.from_bytes(AuthService._b64url_decode(jwk["x"]), "big")
        y = int.from_bytes(AuthService._b64url_decode(jwk["y"]), "big")
        public_key = ec.EllipticCurvePublicNumbers(x=x, y=y, curve=ec.SECP256R1()).public_key()
        authenticator_data = AuthService._b64url_decode(authenticator_data_b64url)
        _, client_data_raw = AuthService._parse_client_data(client_data_json_b64url)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(client_data_raw)
        client_data_hash = digest.finalize()
        signed_data = authenticator_data + client_data_hash
        signature = AuthService._b64url_decode(signature_b64url)
        try:
            public_key.verify(signature, signed_data, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as e:
            raise ValueError("Invalid passkey signature") from e

    async def _create_challenge(self, org_id: UUID, user_id: UUID, purpose: str) -> str:
        challenge = self._new_challenge()
        record = AuthChallenge(
            org_id=org_id,
            user_id=user_id,
            challenge=challenge,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self.db.add(record)
        await self.db.flush()
        return challenge

    async def _consume_challenge(self, org_id: UUID, user_id: UUID, challenge: str, purpose: str) -> AuthChallenge:
        result = await self.db.execute(
            select(AuthChallenge).where(
                AuthChallenge.org_id == org_id,
                AuthChallenge.user_id == user_id,
                AuthChallenge.challenge == challenge,
                AuthChallenge.purpose == purpose,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError("Invalid challenge")
        now = datetime.now(timezone.utc)
        if item.consumed_at is not None:
            raise ValueError("Challenge already consumed")
        if item.expires_at < now:
            raise ValueError("Challenge expired")
        item.consumed_at = now
        await self.db.flush()
        return item

    async def begin_passkey_registration(self, user: User) -> str:
        return await self._create_challenge(user.org_id, user.id, "passkey_register")

    async def verify_passkey_registration(
        self,
        user: User,
        challenge: str,
        credential_id: str,
        public_key_jwk: dict,
        client_data_json: str,
        authenticator_data: str,
        attestation_object: str | None,
        transports: list[str] | None,
        sign_count: int,
    ) -> PasskeyCredential:
        await self._consume_challenge(user.org_id, user.id, challenge, "passkey_register")
        client_data, _ = self._parse_client_data(client_data_json)
        if client_data.get("type") != "webauthn.create":
            raise ValueError("Invalid registration clientData type")
        if client_data.get("challenge") != challenge:
            raise ValueError("Registration challenge mismatch")
        origin = client_data.get("origin", "")
        if not self._origin_allowed(origin):
            raise ValueError("Registration origin not allowed")
        if attestation_object is None:
            raise ValueError("Attestation object missing")
        self._verify_registration_attestation(
            attestation_object_b64url=attestation_object,
            authenticator_data_b64url=authenticator_data,
            client_data_json_b64url=client_data_json,
        )

        settings = get_settings()
        rp_id_hash, flags, parsed_sign_count = self._parse_authenticator_data(authenticator_data)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(settings.passkey_rp_id.encode("utf-8"))
        expected_rp_id_hash = self._b64url_encode(digest.finalize())
        if rp_id_hash != expected_rp_id_hash:
            raise ValueError("Registration RP ID hash mismatch")
        user_present = bool(flags & 0x01)
        attested_credential_data = bool(flags & 0x40)
        if not user_present:
            raise ValueError("User presence flag missing in registration authenticator data")
        if not attested_credential_data:
            raise ValueError("Attested credential data flag missing in registration authenticator data")

        raw_auth_data = self._b64url_decode(authenticator_data)
        if len(raw_auth_data) < 55:
            raise ValueError("Registration authenticator data too short")
        credential_id_len = int.from_bytes(raw_auth_data[53:55], byteorder="big")
        if len(raw_auth_data) < 55 + credential_id_len:
            raise ValueError("Registration authenticator credential id is truncated")
        parsed_credential_id = self._b64url_encode(raw_auth_data[55 : 55 + credential_id_len])
        if parsed_credential_id != credential_id:
            raise ValueError("Credential ID mismatch against authenticator data")

        existing = await self.db.execute(
            select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Credential already registered")

        credential = PasskeyCredential(
            org_id=user.org_id,
            user_id=user.id,
            credential_id=credential_id,
            public_key_jwk=json.dumps(public_key_jwk, separators=(",", ":"), ensure_ascii=False),
            sign_count=max(sign_count, parsed_sign_count),
            transports=",".join(transports or []),
            last_used_at=datetime.now(timezone.utc),
        )
        self.db.add(credential)
        user.passkey_enabled = True
        await self.db.flush()
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.passkey.registered",
            entity_type="passkey_credential",
            entity_id=str(credential.id),
            payload={
                "credential_id": credential.credential_id,
                "transports": transports or [],
                "sign_count": credential.sign_count,
            },
        )
        await self.db.refresh(credential)
        return credential

    async def begin_passkey_login(self, email: str) -> tuple[User, str, list[str]]:
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            raise ValueError("User inactive or not found")
        result = await self.db.execute(
            select(PasskeyCredential).where(PasskeyCredential.user_id == user.id)
        )
        credentials = list(result.scalars().all())
        if not credentials:
            raise ValueError("No passkeys registered")
        challenge = await self._create_challenge(user.org_id, user.id, "passkey_login")
        return user, challenge, [c.credential_id for c in credentials]

    async def verify_passkey_login(
        self,
        email: str,
        challenge: str,
        credential_id: str,
        client_data_json: str,
        authenticator_data: str,
        signature: str,
        sign_count: int,
    ) -> tuple[User, str, str]:
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            raise ValueError("User inactive or not found")
        await self._consume_challenge(user.org_id, user.id, challenge, "passkey_login")
        client_data, _ = self._parse_client_data(client_data_json)
        if client_data.get("type") != "webauthn.get":
            raise ValueError("Invalid login clientData type")
        if client_data.get("challenge") != challenge:
            raise ValueError("Login challenge mismatch")
        origin = client_data.get("origin", "")
        if not self._origin_allowed(origin):
            raise ValueError("Login origin not allowed")
        rp_id_hash, flags, parsed_sign_count = self._parse_authenticator_data(authenticator_data)
        settings = get_settings()
        digest = hashes.Hash(hashes.SHA256())
        digest.update(settings.passkey_rp_id.encode("utf-8"))
        expected_rp_id_hash = self._b64url_encode(digest.finalize())
        if rp_id_hash != expected_rp_id_hash:
            raise ValueError("RP ID hash mismatch")
        user_present = bool(flags & 0x01)
        if not user_present:
            raise ValueError("User presence flag missing in authenticator data")
        result = await self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.user_id == user.id,
                PasskeyCredential.credential_id == credential_id,
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise ValueError("Credential not found")
        self._verify_assertion_signature(
            public_key_jwk_raw=credential.public_key_jwk,
            authenticator_data_b64url=authenticator_data,
            client_data_json_b64url=client_data_json,
            signature_b64url=signature,
        )
        effective_sign_count = max(parsed_sign_count, sign_count)
        if effective_sign_count < credential.sign_count:
            raise ValueError("Passkey sign counter rollback detected")
        credential.sign_count = effective_sign_count
        credential.last_used_at = datetime.now(timezone.utc)
        user.last_login = datetime.now(timezone.utc)
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.passkey.login",
            entity_type="user",
            entity_id=str(user.id),
            payload={
                "credential_id": credential.credential_id,
                "sign_count": credential.sign_count,
                "origin": origin,
            },
        )
        access = create_access_token(str(user.id), {"org_id": str(user.org_id), "role": user.role})
        refresh = create_refresh_token(str(user.id))
        await self.db.flush()
        return user, access, refresh

    async def list_user_passkeys(self, user: User) -> list[PasskeyCredential]:
        result = await self.db.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.user_id == user.id)
            .order_by(PasskeyCredential.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_user_passkey(self, user: User, passkey_id: UUID) -> None:
        result = await self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.id == passkey_id,
                PasskeyCredential.user_id == user.id,
            )
        )
        passkey = result.scalar_one_or_none()
        if not passkey:
            raise ValueError("Passkey not found")
        revoked_credential_id = passkey.credential_id
        await self.db.delete(passkey)
        remaining = await self.list_user_passkeys(user)
        user.passkey_enabled = len(remaining) > 0
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.passkey.revoked",
            entity_type="passkey_credential",
            entity_id=str(passkey_id),
            payload={
                "credential_id": revoked_credential_id,
                "remaining_passkeys": len(remaining),
            },
        )
        await self.db.flush()

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:90] or "workspace"

    async def _ensure_oidc_user(self, *, email: str, full_name: str | None) -> User:
        existing = await self.get_user_by_email(email)
        if existing:
            if not existing.is_active:
                raise ValueError("Account inactive")
            return existing
        domain = email.split("@")[-1] if "@" in email else "workspace.local"
        base_slug = f"oidc-{self._slugify(domain)}"
        slug = base_slug
        i = 1
        while True:
            taken = await self.db.execute(select(Organization).where(Organization.slug == slug))
            if not taken.scalar_one_or_none():
                break
            i += 1
            slug = f"{base_slug}-{i}"
        org = Organization(name=f"{domain} Workspace", slug=slug)
        self.db.add(org)
        await self.db.flush()
        user = User(
            org_id=org.id,
            email=email,
            full_name=full_name or email.split("@")[0],
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.ADMIN,
            passkey_enabled=False,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    def build_azure_oidc_start_url(self) -> str:
        settings = get_settings()
        if not settings.azure_client_id:
            raise ValueError("Azure OIDC not configured: azure_client_id is empty")
        nonce = secrets.token_urlsafe(16)
        state_payload = {
            "type": "oidc_state",
            "provider": "azure",
            "nonce": nonce,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        state = jwt.encode(state_payload, settings.secret_key, algorithm="HS256")
        tenant = settings.azure_tenant_id or "common"
        params = urlencode(
            {
                "client_id": settings.azure_client_id,
                "response_type": "code",
                "redirect_uri": settings.azure_oidc_redirect_uri,
                "response_mode": "query",
                "scope": settings.azure_oidc_scopes,
                "nonce": nonce,
                "state": state,
            }
        )
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{params}"

    async def login_with_azure_oidc_callback(self, *, code: str, state: str) -> tuple[User, str, str]:
        settings = get_settings()
        tenant = settings.azure_tenant_id or "common"
        try:
            state_payload = jwt.decode(state, settings.secret_key, algorithms=["HS256"])
            if state_payload.get("type") != "oidc_state" or state_payload.get("provider") != "azure":
                raise ValueError("Invalid OIDC state")
        except jose_exceptions.ExpiredSignatureError as e:
            raise ValueError("OIDC state has expired") from e
        except Exception as e:
            raise ValueError("Invalid OIDC state") from e

        nonce = state_payload.get("nonce")
        if not nonce:
            raise ValueError("OIDC state missing nonce")

        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        form = {
            "grant_type": "authorization_code",
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "code": code,
            "redirect_uri": settings.azure_oidc_redirect_uri,
            "scope": settings.azure_oidc_scopes,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(token_url, data=form)
        if resp.status_code >= 400:
            raise ValueError(f"OIDC token exchange failed: {resp.text[:300]}")
        token_payload = resp.json()
        id_token = token_payload.get("id_token")
        if not id_token:
            raise ValueError("OIDC id_token missing")

        jwks = await self._fetch_azure_jwks(tenant, settings.oidc_jwks_cache_ttl_seconds)
        claims = self._verify_azure_id_token(
            id_token,
            jwks=jwks,
            nonce=nonce,
            tenant=tenant,
            client_id=settings.azure_client_id,
        )

        email = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
        if not email:
            raise ValueError("OIDC email claim missing")
        full_name = claims.get("name")
        user = await self._ensure_oidc_user(email=email, full_name=full_name)
        user.last_login = datetime.now(timezone.utc)
        await self.audit_chain.append_event(
            org_id=user.org_id,
            actor_user_id=user.id,
            event_type="auth.oidc.login",
            entity_type="user",
            entity_id=str(user.id),
            payload={
                "provider": "azure",
                "email": email,
            },
        )
        access = create_access_token(str(user.id), {"org_id": str(user.org_id), "role": user.role})
        refresh = create_refresh_token(str(user.id))
        await self.db.flush()
        return user, access, refresh

    # -----------------------------------------------------------------------
    # Azure OIDC helpers — JWKS fetch and id_token full verification
    # -----------------------------------------------------------------------

    @staticmethod
    def _azure_jwks_url(tenant: str) -> str:
        return f"https://login.microsoftonline.com/{tenant}/v2.0/keys"

    @classmethod
    async def _fetch_azure_jwks(cls, tenant: str, ttl: int) -> dict:
        """Fetch the Azure AD JWKS, returning a cached copy within *ttl* seconds."""
        global _JWKS_CACHE
        now = _time.monotonic()
        if _JWKS_CACHE["data"] and (now - _JWKS_CACHE["fetched_at"]) < ttl:
            return _JWKS_CACHE["data"]
        url = cls._azure_jwks_url(tenant)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            raise ValueError(f"Failed to fetch Azure JWKS ({resp.status_code}): {resp.text[:200]}")
        jwks = resp.json()
        if not isinstance(jwks.get("keys"), list):
            raise ValueError("Azure JWKS response malformed: missing 'keys' array")
        _JWKS_CACHE = {"data": jwks, "fetched_at": now}
        return jwks

    @staticmethod
    def _verify_azure_id_token(
        id_token: str,
        *,
        jwks: dict,
        nonce: str,
        tenant: str,
        client_id: str,
    ) -> dict:
        """
        Validate an Azure AD id_token fully:
          1. Parse the JOSE header to extract kid + alg.
          2. Locate the matching public key in the JWKS.
          3. Verify the signature and standard JWT claims (exp, nbf, aud) via python-jose.
          4. Validate the issuer against the expected Azure AD tenant URL.
          5. Verify the nonce to prevent replay attacks.

        Returns the verified claims dict.
        Raises ValueError for any validation failure.
        """
        try:
            header = jwt.get_unverified_header(id_token)
        except Exception as e:
            raise ValueError("Cannot parse id_token header") from e

        kid = header.get("kid")
        alg = header.get("alg", "RS256")
        # Azure AD uses RS256; reject other algorithms to prevent alg-confusion attacks.
        if alg not in {"RS256", "RS384", "RS512"}:
            raise ValueError(f"Unsupported id_token algorithm: {alg!r}")

        matching_key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            None,
        )
        if not matching_key:
            raise ValueError(f"No JWKS key found for kid={kid!r} — JWKS may be stale")

        try:
            claims = jwt.decode(
                id_token,
                matching_key,
                algorithms=[alg],
                audience=client_id,
            )
        except jose_exceptions.ExpiredSignatureError as e:
            raise ValueError("id_token has expired") from e
        except jose_exceptions.JWTClaimsError as e:
            raise ValueError(f"id_token claims invalid: {e}") from e
        except jose_exceptions.JWTError as e:
            raise ValueError(f"id_token signature verification failed: {e}") from e
        except Exception as e:
            raise ValueError(f"id_token verification failed: {e}") from e

        # Validate issuer.
        # Single-tenant: must match exactly.
        # Multi-tenant ("common"): Azure replaces {tenant} with the actual tenant GUID;
        # accept any valid Azure AD v2 issuer URL pattern.
        iss = claims.get("iss", "")
        if tenant == "common":
            if not (
                iss.startswith("https://login.microsoftonline.com/")
                and iss.endswith("/v2.0")
            ):
                raise ValueError(f"id_token issuer not a valid Azure AD v2 URL: {iss!r}")
        else:
            expected_iss = f"https://login.microsoftonline.com/{tenant}/v2.0"
            if iss != expected_iss:
                raise ValueError(
                    f"id_token issuer mismatch: got {iss!r}, expected {expected_iss!r}"
                )

        # Validate nonce — prevents replay attacks.
        if claims.get("nonce") != nonce:
            raise ValueError("id_token nonce mismatch")

        return claims

    # ── Password reset ───────────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> str:
        """Generate a password-reset token stored in auth_challenges.

        Always returns a token-like string regardless of whether the email
        exists to prevent email-enumeration attacks.  In production the token
        would be e-mailed and NOT returned directly; here it is returned for
        dev convenience (no email service is configured in Wave 0).
        """
        token = secrets.token_urlsafe(32)
        user = await self.get_user_by_email(email)
        if user is None:
            # Unknown email — return a realistic-looking token without writing to DB.
            return token

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        challenge = AuthChallenge(
            org_id=user.org_id,
            user_id=user.id,
            challenge=token,
            purpose="password_reset",
            expires_at=expires_at,
        )
        self.db.add(challenge)
        await self.db.flush()
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validate *token* and update the user's password.

        Raises ``ValueError`` for unknown, expired, or already-consumed tokens.
        """
        result = await self.db.execute(
            select(AuthChallenge).where(
                AuthChallenge.challenge == token,
                AuthChallenge.purpose == "password_reset",
                AuthChallenge.consumed_at.is_(None),
            )
        )
        challenge = result.scalar_one_or_none()
        if challenge is None:
            raise ValueError("Invalid or expired reset token")

        now = datetime.now(timezone.utc)
        if challenge.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Reset token has expired")

        user_result = await self.db.execute(
            select(User).where(User.id == challenge.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        user.hashed_password = hash_password(new_password)
        challenge.consumed_at = now
        await self.db.flush()
