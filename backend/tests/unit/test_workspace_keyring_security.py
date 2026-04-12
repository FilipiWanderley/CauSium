from uuid import uuid4

import pytest

from app.core.security import (
    decrypt_secret,
    decrypt_secret_for_org,
    encrypt_secret,
    encrypt_secret_for_org,
    ensure_workspace_keyring,
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
