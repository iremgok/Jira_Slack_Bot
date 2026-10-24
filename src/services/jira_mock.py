"""
Offline stand-in for ``JiraClient`` (enabled with ``JIRA_MOCK_MODE=true``).

Returns realistic sample issues with timestamps relative to "now", so the
poller and the daily report can be exercised without a Jira account.
The JQL is logged but not interpreted.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.models.issue import JiraIssue

logger = logging.getLogger(__name__)


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000%z")


def _raw(key: str, summary: str, status: str, category: str, priority: str,
         assignee: str | None, created: datetime, updated: datetime,
         resolved: datetime | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status, "statusCategory": {"key": category}},
            "priority": {"name": priority},
            "assignee": {"displayName": assignee} if assignee else None,
            "issuetype": {"name": "Task"},
            "created": _ts(created),
            "updated": _ts(updated),
            "resolutiondate": _ts(resolved) if resolved else None,
            "statuscategorychangedate": _ts(resolved or updated) if category == "done" else None,
        },
    }


class MockJiraClient:
    """Implements the ``IssueSource`` protocol with in-memory sample data."""

    def __init__(self, base_url: str, project_key: str) -> None:
        self.base_url = base_url
        now = datetime.now(timezone.utc)
        p = project_key
        self._raw_issues = [
            _raw(f"{p}-101", "Ödeme sayfasında 500 hatası alınıyor", "In Progress",
                 "indeterminate", "Highest", "Ahmet Yılmaz",
                 now - timedelta(hours=3), now - timedelta(minutes=20)),
            _raw(f"{p}-102", "Slack entegrasyonu tamamlandı", "Done", "done", "Medium",
                 "İrem", now - timedelta(days=2), now - timedelta(hours=1),
                 resolved=now - timedelta(hours=1)),
            _raw(f"{p}-103", "Login ekranında şifre sıfırlama linki çalışmıyor", "To Do",
                 "new", "High", "Ahmet Yılmaz",
                 now - timedelta(hours=5), now - timedelta(hours=5)),
            _raw(f"{p}-104", "Rapor ekranına CSV dışa aktarma ekle", "In Review",
                 "indeterminate", "Low", "Zeynep Kaya",
                 now - timedelta(days=4), now - timedelta(hours=2)),
            _raw(f"{p}-105", "Mobil uygulamada bildirim izni sorunu", "To Do",
                 "new", "Medium", None,
                 now - timedelta(minutes=40), now - timedelta(minutes=40)),
        ]

    def search_issues(self, jql: str, limit: int | None = None) -> list[JiraIssue]:
        logger.info("[MOCK] Returning sample issues for JQL: %s", jql)
        issues = [JiraIssue.from_api(raw, self.base_url) for raw in self._raw_issues]
        return issues[:limit] if limit is not None else issues

    def health_check(self) -> bool:
        return True

    def close(self) -> None:
        pass
