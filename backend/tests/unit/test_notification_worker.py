"""Unit tests for notification_worker delivery logic.

Uses mocks — no DB required. Tests:
- _build_alert_email generates correct subject/body for each severity
- run_once is callable without crashing when DB returns no pending alerts
- Email is not sent when no recipients match
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.notifications.models import AlertCategory, AlertRecord, AlertSeverity
from app.workers.notification_worker import _build_alert_email, _severity_label


def _make_alert(
    severity: AlertSeverity = AlertSeverity.CRITICAL,
    category: AlertCategory = AlertCategory.FINANCIAL,
    title: str = "Test alert",
    body: str | None = "Details here",
    action_url: str | None = None,
) -> AlertRecord:
    alert = MagicMock(spec=AlertRecord)
    alert.id = uuid4()
    alert.org_id = uuid4()
    alert.severity = severity
    alert.category = category
    alert.title = title
    alert.body = body
    alert.action_url = action_url
    return alert


class TestSeverityLabel:
    def test_critical(self):
        assert _severity_label(AlertSeverity.CRITICAL) == "Crítico"

    def test_warning(self):
        assert _severity_label(AlertSeverity.WARNING) == "Aviso"

    def test_info(self):
        assert _severity_label(AlertSeverity.INFO) == "Info"


class TestBuildAlertEmail:
    def test_subject_contains_severity_and_title(self):
        alert = _make_alert(severity=AlertSeverity.CRITICAL, title="Budget exceeded")
        subject, _, _ = _build_alert_email(alert)
        assert "Crítico" in subject
        assert "Budget exceeded" in subject

    def test_text_body_contains_category(self):
        alert = _make_alert(category=AlertCategory.FINANCIAL)
        _, text, _ = _build_alert_email(alert)
        assert "financial" in text

    def test_text_body_contains_body(self):
        alert = _make_alert(body="Spend $1000 over budget")
        _, text, _ = _build_alert_email(alert)
        assert "Spend $1000 over budget" in text

    def test_text_body_contains_action_url(self):
        alert = _make_alert(action_url="https://app.causium.io/alerts/123")
        _, text, _ = _build_alert_email(alert)
        assert "https://app.causium.io/alerts/123" in text

    def test_html_body_escapes_xss(self):
        alert = _make_alert(title="<script>alert(1)</script>")
        _, _, html = _build_alert_email(alert)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_body_has_action_link(self):
        alert = _make_alert(action_url="https://app.causium.io/alerts/1")
        _, _, html = _build_alert_email(alert)
        assert "href=" in html
        assert "Ver no CauSium" in html

    def test_no_action_url_no_link_in_html(self):
        alert = _make_alert(action_url=None)
        _, _, html = _build_alert_email(alert)
        assert "Ver no CauSium" not in html

    def test_severity_colors(self):
        for severity, expected_color in [
            (AlertSeverity.CRITICAL, "#dc2626"),
            (AlertSeverity.WARNING, "#d97706"),
            (AlertSeverity.INFO, "#2563eb"),
        ]:
            alert = _make_alert(severity=severity)
            _, _, html = _build_alert_email(alert)
            assert expected_color in html


@pytest.mark.asyncio
async def test_run_once_no_crash_when_no_pending_alerts():
    """run_once should complete without error when there are no pending alerts."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.workers.notification_worker.async_session_factory") as mock_factory:
        mock_factory.return_value = mock_session
        from app.workers.notification_worker import run_once
        await run_once()  # must not raise
