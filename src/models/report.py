"""
Daily report model and the pure logic that computes it from issues.

Keeping the computation free of I/O makes it trivial to unit test and
independent of where the issues come from (Jira, mock data, database).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from src.models.issue import JiraIssue


class AssigneeLoad(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    open_issues: int


class DailyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_date: date
    created: list[JiraIssue]
    closed: list[JiraIssue]
    open_critical: list[JiraIssue]
    top_assignees: list[AssigneeLoad]
    total_open: int


def _in_window(moment: datetime | None, start: datetime, end: datetime) -> bool:
    return moment is not None and start <= moment < end


def compute_daily_report(
    issues: list[JiraIssue],
    window_start: datetime,
    window_end: datetime,
    critical_priorities: set[str],
    top_n: int = 5,
) -> DailyReport:
    """
    Summarize a day of activity.

    * created        -> issues created inside the window
    * closed         -> done issues resolved inside the window
    * open_critical  -> currently open issues with a critical priority
    * top_assignees  -> people holding the most open issues
    """
    unique = {issue.key: issue for issue in issues}.values()

    created = [i for i in unique if _in_window(i.created, window_start, window_end)]
    closed = [
        i for i in unique
        if i.is_done and _in_window(i.resolved or i.updated, window_start, window_end)
    ]
    open_issues = [i for i in unique if not i.is_done]
    open_critical = sorted(
        (i for i in open_issues if i.is_critical(critical_priorities)),
        key=lambda i: i.created,
    )

    load = Counter(i.assignee_display for i in open_issues)
    top_assignees = [AssigneeLoad(name=n, open_issues=c) for n, c in load.most_common(top_n)]

    return DailyReport(
        report_date=window_start.date(),
        created=sorted(created, key=lambda i: i.created),
        closed=sorted(closed, key=lambda i: i.resolved or i.updated),
        open_critical=open_critical,
        top_assignees=top_assignees,
        total_open=len(open_issues),
    )
