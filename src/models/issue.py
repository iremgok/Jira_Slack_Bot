"""
Domain models for Jira issues.

``JiraIssue.from_api`` turns the raw Jira REST JSON into a typed, validated
object. The rest of the application only works with these models and never
touches raw Jira payloads.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

UNASSIGNED = "Unassigned"
DONE_CATEGORY = "done"

# Fields requested from Jira; keeps responses small
JIRA_FIELDS = "summary,status,assignee,priority,issuetype,created,updated,resolutiondate,statuscategorychangedate"


def parse_jira_datetime(value: Any) -> datetime | None:
    """Parse Jira timestamps like ``2026-08-18T10:00:00.000+0300`` into aware UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f%z")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class JiraIssue(BaseModel):
    """A normalized Jira issue."""

    model_config = ConfigDict(frozen=True)

    key: str
    summary: str
    status: str
    status_category: str = ""
    assignee: str | None = None
    priority: str = "None"
    issue_type: str = ""
    created: datetime
    updated: datetime
    resolved: datetime | None = None
    status_category_changed: datetime | None = None
    url: str = ""

    @field_validator("created", "updated", "resolved", "status_category_changed", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> datetime | None:
        return parse_jira_datetime(value)

    @classmethod
    def from_api(cls, raw: dict[str, Any], base_url: str) -> "JiraIssue":
        """Build an issue from a single element of Jira's ``issues`` array."""
        fields = raw.get("fields") or {}
        status = fields.get("status") or {}
        assignee = fields.get("assignee") or {}
        priority = fields.get("priority") or {}
        issue_type = fields.get("issuetype") or {}
        key = raw["key"]

        return cls(
            key=key,
            summary=fields.get("summary") or "(no summary)",
            status=status.get("name", "Unknown"),
            status_category=(status.get("statusCategory") or {}).get("key", ""),
            assignee=assignee.get("displayName"),
            priority=priority.get("name", "None"),
            issue_type=issue_type.get("name", ""),
            created=fields.get("created"),
            updated=fields.get("updated"),
            resolved=fields.get("resolutiondate"),
            status_category_changed=fields.get("statuscategorychangedate"),
            url=f"{base_url.rstrip('/')}/browse/{key}",
        )

    @property
    def assignee_display(self) -> str:
        return self.assignee or UNASSIGNED

    @property
    def is_done(self) -> bool:
        if self.status_category:
            return self.status_category == DONE_CATEGORY
        return self.resolved is not None

    @property
    def closed_at(self) -> datetime:
        """
        Best estimate of when a done issue was closed. Many Jira workflows never
        set ``resolutiondate``, so fall back to the status-category change time.
        """
        return self.resolved or self.status_category_changed or self.updated

    def is_critical(self, critical_priorities: set[str]) -> bool:
        return self.priority.lower() in critical_priorities


class FieldChange(BaseModel):
    """A single tracked field change between two snapshots of an issue."""

    model_config = ConfigDict(frozen=True)

    field: str
    old: str
    new: str


TRACKED_FIELDS: dict[str, str] = {
    "status": "Status",
    "priority": "Priority",
    "assignee_display": "Assignee",
    "summary": "Summary",
}


def detect_changes(previous: JiraIssue, current: JiraIssue) -> list[FieldChange]:
    """Return the human-relevant differences between two snapshots."""
    changes: list[FieldChange] = []
    for attr, label in TRACKED_FIELDS.items():
        old_value, new_value = getattr(previous, attr), getattr(current, attr)
        if old_value != new_value:
            changes.append(FieldChange(field=label, old=str(old_value), new=str(new_value)))
    return changes
