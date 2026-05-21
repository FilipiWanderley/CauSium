from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domains.auth.models import User, UserRole
from app.workers.maintenance_worker import _run_user_retention_anonymization


class _FakeScalarResult:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    def all(self) -> list[User]:
        return self._users


class _FakeExecuteResult:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._users)


class _FakeSession:
    def __init__(self, users: list[User]) -> None:
        self._users = users
        self.commit_calls = 0

    async def execute(self, _query):
        return _FakeExecuteResult(self._users)

    async def commit(self) -> None:
        self.commit_calls += 1


def _make_inactive_user(*, suffix: str, deleted_at: datetime, email: str | None = None) -> User:
    return User(
        id=uuid4(),
        email=email or f"user-{suffix}@retention.example.com",
        full_name="Retention User",
        hashed_password="hashed",
        role=UserRole.VIEWER,
        is_active=False,
        deleted_at=deleted_at,
    )


@pytest.mark.asyncio
async def test_retention_policy_anonymizes_user_deleted_more_than_30_days(monkeypatch):
    old_deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
    user = _make_inactive_user(suffix=uuid4().hex[:8], deleted_at=old_deleted_at)
    original_email = user.email
    fake_session = _FakeSession([user])

    @asynccontextmanager
    async def fake_async_session_factory():
        yield fake_session

    monkeypatch.setattr("app.workers.maintenance_worker.async_session_factory", fake_async_session_factory)

    changed = await _run_user_retention_anonymization()
    assert changed == 1

    assert user.email != original_email
    assert user.email.endswith("@deleted.invalid")
    assert user.full_name == "Deleted User"
    assert fake_session.commit_calls == 1


@pytest.mark.asyncio
async def test_retention_policy_keeps_recently_deleted_user_unchanged(monkeypatch):
    recent_deleted_at = datetime.now(timezone.utc) - timedelta(days=7)
    user = _make_inactive_user(suffix=uuid4().hex[:8], deleted_at=recent_deleted_at)
    original_email = user.email
    original_name = user.full_name
    fake_session = _FakeSession([])

    @asynccontextmanager
    async def fake_async_session_factory():
        yield fake_session

    monkeypatch.setattr("app.workers.maintenance_worker.async_session_factory", fake_async_session_factory)

    changed = await _run_user_retention_anonymization()
    assert changed == 0

    assert user.email == original_email
    assert user.full_name == original_name
    assert fake_session.commit_calls == 0
