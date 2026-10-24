from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from src.core.exceptions import SlackError
from src.database.db import Database
from src.models.issue import JiraIssue

BASE_URL = "https://example.atlassian.net"
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def raw_issue(key: str = "KAN-1", *, status: str = "To Do", category: str = "new",
              priority: str = "Medium", assignee: str | None = "Ayşe",
              created: datetime = NOW, updated: datetime | None = None,
              resolved: datetime | None = None, status_changed: datetime | None = None,
              summary: str = "Fix bug") -> dict[str, Any]:
    fmt = "%Y-%m-%dT%H:%M:%S.000%z"
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status, "statusCategory": {"key": category}},
            "priority": {"name": priority},
            "assignee": {"displayName": assignee} if assignee else None,
            "issuetype": {"name": "Bug"},
            "created": created.strftime(fmt),
            "updated": (updated or created).strftime(fmt),
            "resolutiondate": resolved.strftime(fmt) if resolved else None,
            "statuscategorychangedate": status_changed.strftime(fmt) if status_changed else None,
        },
    }


def make_issue(key: str = "KAN-1", **kwargs: Any) -> JiraIssue:
    return JiraIssue.from_api(raw_issue(key, **kwargs), BASE_URL)


class FakeJira:
    def __init__(self, issues: list[JiraIssue] | None = None) -> None:
        self.issues = issues or []
        self.queries: list[str] = []

    def search_issues(self, jql: str, limit: int | None = None) -> list[JiraIssue]:
        self.queries.append(jql)
        return list(self.issues)

    def close(self) -> None:
        pass


class FakeSlack:
    def __init__(self, fail_keys: set[str] | None = None) -> None:
        self.messages = []
        self.fail_keys = fail_keys or set()

    def send(self, message) -> None:
        if any(key in message.text for key in self.fail_keys):
            raise SlackError("boom")
        self.messages.append(message)


@pytest.fixture
def database():
    db = Database("sqlite:///:memory:")
    db.create_tables()
    yield db
    db.dispose()
