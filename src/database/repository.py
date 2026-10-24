"""
Repositories: the only place that knows about ORM tables.

They accept and return domain models (``JiraIssue``, ``DailyReport``) so the
jobs never deal with SQLAlchemy objects directly.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.exceptions import RepositoryError
from src.database.tables import JobState, SentReport, TrackedIssue
from src.models.issue import JiraIssue, parse_jira_datetime
from src.models.report import DailyReport


def _to_model(row: TrackedIssue) -> JiraIssue:
    return JiraIssue(
        key=row.key,
        summary=row.summary,
        status=row.status,
        status_category=row.status_category,
        assignee=row.assignee,
        priority=row.priority,
        issue_type=row.issue_type,
        created=row.created,
        updated=row.updated,
        resolved=row.resolved,
        url=row.url,
    )


class IssueRepository:
    """Stores the last known snapshot of every issue the bot has seen."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_snapshots(self, keys: list[str]) -> dict[str, JiraIssue]:
        if not keys:
            return {}
        try:
            rows = self.session.scalars(select(TrackedIssue).where(TrackedIssue.key.in_(keys)))
            return {row.key: _to_model(row) for row in rows}
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Failed to load issue snapshots: {exc}") from exc

    def upsert(self, issue: JiraIssue) -> None:
        try:
            row = self.session.get(TrackedIssue, issue.key)
            if row is None:
                row = TrackedIssue(key=issue.key)
                self.session.add(row)
            row.summary = issue.summary
            row.status = issue.status
            row.status_category = issue.status_category
            row.assignee = issue.assignee
            row.priority = issue.priority
            row.issue_type = issue.issue_type
            row.url = issue.url
            row.created = issue.created
            row.updated = issue.updated
            row.resolved = issue.resolved
            self.session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Failed to save issue {issue.key}: {exc}") from exc

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(TrackedIssue)) or 0


class JobStateRepository:
    """Persists small pieces of job state such as the last poll time."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_datetime(self, name: str) -> datetime | None:
        row = self.session.get(JobState, name)
        return parse_jira_datetime(row.value) if row else None

    def set_datetime(self, name: str, value: datetime) -> None:
        try:
            row = self.session.get(JobState, name)
            if row is None:
                self.session.add(JobState(name=name, value=value.isoformat()))
            else:
                row.value = value.isoformat()
            self.session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Failed to save job state '{name}': {exc}") from exc


class ReportRepository:
    """Keeps a log of delivered daily reports for idempotency."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def was_sent(self, report_date: date) -> bool:
        stmt = select(SentReport.id).where(SentReport.report_date == report_date)
        return self.session.scalar(stmt) is not None

    def record(self, report: DailyReport) -> None:
        try:
            self.session.add(
                SentReport(
                    report_date=report.report_date,
                    created_count=len(report.created),
                    closed_count=len(report.closed),
                    open_critical_count=len(report.open_critical),
                )
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Failed to record report: {exc}") from exc
