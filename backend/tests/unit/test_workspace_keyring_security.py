from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import (
    decrypt_secret,
    decrypt_secret_for_org,
    encrypt_secret,
    encrypt_secret_for_org,
    ensure_workspace_keyring,
    rotate_expired_workspace_keyrings,
)
from app.domains.auth.models import Organization, WorkspaceKeyring


@pytest.mark.asyncio
async def test_workspace_keyring_encrypt_decrypt_isolated_per_org(db):
    org_a = Organization(name="Org A", slug=f"org-a-{uuid4().hex[:8]}")
    org_b = Organization(name="Org B", slug=f"org-b-{uuid4().hex[:8]}")
    db.add_all([org_a, org_b])
    await db.flush()

    encrypted_a = await encrypt_secret_for_org(db, org_a.id, "secret-a")
    encrypted_b = await encrypt_secret_for_org(db, org_b.id, "secret-b")

    assert encrypted_a.startswith("wk1:1:")
    assert encrypted_b.startswith("wk1:1:")

    assert await decrypt_secret_for_org(db, org_a.id, encrypted_a) == "secret-a"
    assert await decrypt_secret_for_org(db, org_b.id, encrypted_b) == "secret-b"

    with pytest.raises(ValueError):
        await decrypt_secret_for_org(db, org_b.id, encrypted_a)


@pytest.mark.asyncio
async def test_workspace_keyring_legacy_ciphertext_still_supported(db):
    org = Organization(name="Org Legacy", slug=f"org-legacy-{uuid4().hex[:8]}")
    db.add(org)
    await db.flush()

    legacy = encrypt_secret("legacy-value")
    assert await decrypt_secret_for_org(db, org.id, legacy) == "legacy-value"
    assert decrypt_secret(legacy) == "legacy-value"


@pytest.mark.asyncio
async def test_ensure_workspace_keyring_idempotent(db):
    org = Organization(name="Org Key", slug=f"org-key-{uuid4().hex[:8]}")
    db.add(org)
    await db.flush()

    first = await ensure_workspace_keyring(db, org.id)
    second = await ensure_workspace_keyring(db, org.id)

    assert first.id == second.id

    rows = await db.execute(
        WorkspaceKeyring.__table__.select().where(WorkspaceKeyring.org_id == org.id)
    )
    assert len(rows.fetchall()) == 1


@pytest.mark.asyncio
async def test_rotate_expired_workspace_keyrings_creates_new_active_version(db):
    org = Organization(name="Org Rotate", slug=f"org-rotate-{uuid4().hex[:8]}")
    db.add(org)
    await db.flush()

    old_secret = await encrypt_secret_for_org(db, org.id, "before-rotation")
    current = await ensure_workspace_keyring(db, org.id)
    current.rotated_at = datetime.now(timezone.utc) - timedelta(days=45)
    await db.flush()

    stats = await rotate_expired_workspace_keyrings(db, max_age_days=30, batch_size=100)
    await db.flush()

    assert stats == {"checked": 1, "rotated": 1}

    keyrings_result = await db.execute(
        select(WorkspaceKeyring)
        .where(WorkspaceKeyring.org_id == org.id)
        .order_by(WorkspaceKeyring.key_version.asc())
    )
    keyrings = list(keyrings_result.scalars().all())

    assert len(keyrings) == 2
    assert keyrings[0].key_version == 1
    assert keyrings[0].is_active is False
    assert keyrings[1].key_version == 2
    assert keyrings[1].is_active is True

    new_secret = await encrypt_secret_for_org(db, org.id, "after-rotation")
    assert new_secret.startswith("wk1:2:")
    assert await decrypt_secret_for_org(db, org.id, old_secret) == "before-rotation"
    assert await decrypt_secret_for_org(db, org.id, new_secret) == "after-rotation"


@pytest.mark.asyncio
async def test_rotate_expired_workspace_keyrings_skips_fresh_keyrings(db):
    org = Organization(name="Org Fresh", slug=f"org-fresh-{uuid4().hex[:8]}")
    db.add(org)
    await db.flush()

    await ensure_workspace_keyring(db, org.id)
    stats = await rotate_expired_workspace_keyrings(db, max_age_days=30)

    assert stats == {"checked": 0, "rotated": 0}

    keyrings_result = await db.execute(
        select(WorkspaceKeyring).where(WorkspaceKeyring.org_id == org.id)
    )
    keyrings = list(keyrings_result.scalars().all())
    assert len(keyrings) == 1
    assert keyrings[0].is_active is True
