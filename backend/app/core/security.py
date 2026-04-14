from __future__ import annotations
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domains.auth.models import WorkspaceKeyring

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
WORKSPACE_CIPHERTEXT_PREFIX = "wk1"


def _fernet_from_settings() -> Fernet:
    """Return a Fernet instance from settings, accepting both raw and base64 keys.

    If ENCRYPTION_KEY is already a valid urlsafe-base64 Fernet key (32-byte
    payload), it is used as-is. Otherwise we derive a stable Fernet key by
    hashing the provided value with SHA-256 and urlsafe-base64-encoding it.
    """
    raw = get_settings().encryption_key.encode()
    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == 32:
            return Fernet(raw)
    except Exception:
        pass

    derived = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(derived)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire, "type": "access", **(extra or {})}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def encrypt_secret(value: str) -> str:
    f = _fernet_from_settings()
    return f.encrypt(value.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    f = _fernet_from_settings()
    return f.decrypt(encrypted.encode()).decode()


def _encrypt_workspace_key_material(raw_workspace_key: str) -> str:
    f = _fernet_from_settings()
    return f.encrypt(raw_workspace_key.encode()).decode()


def _decrypt_workspace_key_material(encrypted_workspace_key: str) -> str:
    f = _fernet_from_settings()
    return f.decrypt(encrypted_workspace_key.encode()).decode()


async def ensure_workspace_keyring(db: AsyncSession, org_id: UUID) -> WorkspaceKeyring:
    result = await db.execute(
        select(WorkspaceKeyring)
        .where(
            WorkspaceKeyring.org_id == org_id,
            WorkspaceKeyring.is_active == True,  # noqa: E712
        )
        .order_by(WorkspaceKeyring.key_version.desc())
        .limit(1)
    )
    current = result.scalar_one_or_none()
    if current is not None:
        return current

    workspace_key = Fernet.generate_key().decode()
    created = WorkspaceKeyring(
        org_id=org_id,
        key_version=1,
        key_material_encrypted=_encrypt_workspace_key_material(workspace_key),
        is_active=True,
        rotated_at=datetime.now(timezone.utc),
    )
    db.add(created)
    await db.flush()
    await db.refresh(created)
    return created


async def encrypt_secret_for_org(db: AsyncSession, org_id: UUID, value: str) -> str:
    keyring = await ensure_workspace_keyring(db, org_id)
    workspace_key = _decrypt_workspace_key_material(keyring.key_material_encrypted)
    token = Fernet(workspace_key.encode()).encrypt(value.encode()).decode()
    return f"{WORKSPACE_CIPHERTEXT_PREFIX}:{keyring.key_version}:{token}"


async def decrypt_secret_for_org(db: AsyncSession, org_id: UUID, encrypted: str) -> str:
    if not encrypted.startswith(f"{WORKSPACE_CIPHERTEXT_PREFIX}:"):
        # Backward compatibility for records encrypted with global key.
        return decrypt_secret(encrypted)

    try:
        _, version_str, token = encrypted.split(":", 2)
        key_version = int(version_str)
    except ValueError as exc:
        raise ValueError("Invalid workspace ciphertext format") from exc

    result = await db.execute(
        select(WorkspaceKeyring).where(
            WorkspaceKeyring.org_id == org_id,
            WorkspaceKeyring.key_version == key_version,
        )
    )
    keyring = result.scalar_one_or_none()
    if keyring is None:
        raise ValueError(f"Workspace keyring not found for org={org_id} version={key_version}")

    workspace_key = _decrypt_workspace_key_material(keyring.key_material_encrypted)
    try:
        return Fernet(workspace_key.encode()).decrypt(token.encode()).decode()
    except Exception as exc:
        raise ValueError("Failed to decrypt workspace-scoped secret") from exc


async def rotate_expired_workspace_keyrings(
    db: AsyncSession,
    *,
    max_age_days: int,
    batch_size: int = 200,
    now: datetime | None = None,
) -> dict[str, int]:
    """Rotate active workspace keyrings older than ``max_age_days``.

    Rotation is append-only for key versions: old keys are kept inactive so
    historic ciphertexts remain decryptable by explicit key version.
    """
    if max_age_days <= 0:
        raise ValueError("max_age_days must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    reference_time = now or datetime.now(timezone.utc)
    cutoff = reference_time - timedelta(days=max_age_days)

    due_result = await db.execute(
        select(WorkspaceKeyring)
        .where(
            WorkspaceKeyring.is_active == True,  # noqa: E712
            or_(
                WorkspaceKeyring.rotated_at.is_(None),
                WorkspaceKeyring.rotated_at <= cutoff,
            ),
        )
        .order_by(WorkspaceKeyring.rotated_at.asc().nullsfirst())
        .limit(batch_size)
    )
    due_keyrings = list(due_result.scalars().all())
    if not due_keyrings:
        return {"checked": 0, "rotated": 0}

    rotated = 0
    for current in due_keyrings:
        max_version_result = await db.execute(
            select(func.max(WorkspaceKeyring.key_version)).where(WorkspaceKeyring.org_id == current.org_id)
        )
        max_version = max_version_result.scalar_one() or 0

        current.is_active = False
        workspace_key = Fernet.generate_key().decode()
        db.add(
            WorkspaceKeyring(
                org_id=current.org_id,
                key_version=max_version + 1,
                key_material_encrypted=_encrypt_workspace_key_material(workspace_key),
                is_active=True,
                rotated_at=reference_time,
            )
        )
        rotated += 1

    await db.flush()
    return {"checked": len(due_keyrings), "rotated": rotated}
