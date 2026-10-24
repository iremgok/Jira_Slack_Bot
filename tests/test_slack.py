from datetime import timedelta

import pytest

from src.core.exceptions import SlackError
from src.models.issue import FieldChange
from src.models.report import compute_daily_report
from src.services.slack_blocks import (
    daily_report_message,
    escape,
    new_issue_message,
    updated_issue_message,
)
from src.services.slack_client import SlackClient
from tests.conftest import NOW, make_issue


def _blocks_text(message) -> str:
    return str(message.blocks)


def test_new_issue_message_has_clickable_link_and_escapes():
    msg = new_issue_message(make_issue("KAN-5", summary="a < b & c"))
    assert "<https://example.atlassian.net/browse/KAN-5|KAN-5 — a &lt; b &amp; c>" in _blocks_text(msg)
    assert msg.text.startswith("🆕")


def test_updated_message_lists_changes():
    msg = updated_issue_message(make_issue(), [FieldChange(field="Status", old="To Do", new="Done")])
    assert "`To Do` → `Done`" in _blocks_text(msg)


def test_daily_report_message_sections():
    start = NOW.replace(hour=0)
    report = compute_daily_report([make_issue(priority="Highest")], start, start + timedelta(days=1), {"highest"})
    text = _blocks_text(daily_report_message(report, "KAN"))
    assert "Open critical issues" in text
    assert "browse/KAN-1" in text


def test_escape():
    assert escape("<&>") == "&lt;&amp;&gt;"


def test_dry_run_does_not_call_network():
    client = SlackClient(dry_run=True)
    client.session = None  # would fail if a request were attempted
    client.send(new_issue_message(make_issue()))


def test_bot_api_error_raises(monkeypatch):
    client = SlackClient(bot_token="xoxb-test", channel="C1")

    class Resp:
        status_code = 200

        def json(self):
            return {"ok": False, "error": "channel_not_found"}

    monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: Resp())
    with pytest.raises(SlackError, match="channel_not_found"):
        client.send(new_issue_message(make_issue()))


def test_webhook_network_error_does_not_leak_url(monkeypatch):
    import requests

    secret_url = "https://hooks.slack.com/services/T000/B000/SECRET123"
    client = SlackClient(webhook_url=secret_url)

    def boom(*args, **kwargs):
        raise requests.ConnectionError(f"Max retries exceeded with url: {secret_url}")

    monkeypatch.setattr(client.session, "post", boom)
    with pytest.raises(SlackError) as exc_info:
        client.send(new_issue_message(make_issue()))
    assert "SECRET123" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None and exc_info.value.__suppress_context__


def test_api_error_includes_hint(monkeypatch):
    client = SlackClient(bot_token="xoxb-test", channel="C1")

    class Resp:
        status_code = 200

        def json(self):
            return {"ok": False, "error": "not_in_channel"}

    monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: Resp())
    with pytest.raises(SlackError, match="/invite"):
        client.send(new_issue_message(make_issue()))


def test_report_sections_stay_within_slack_limits():
    start = NOW.replace(hour=0)
    issues = [make_issue(f"KAN-{n}", priority="Highest", summary="x" * 255) for n in range(30)]
    report = compute_daily_report(issues, start, start + timedelta(days=1), {"highest"})
    for block in daily_report_message(report, "KAN").blocks:
        if block["type"] == "section" and "text" in block:
            assert len(block["text"]["text"]) <= 3000
