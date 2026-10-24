"""
Scheduled job: send a daily summary of Jira activity to Slack.

The report covers the current calendar day in the configured timezone:
issues opened, issues closed, open critical issues and the most loaded
assignees. Each day's report is sent at most once unless forced.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.database.db import Database
from src.database.repository import ReportRepository
from src.models.report import DailyReport, compute_daily_report
from src.services.jira_client import IssueSource, build_jql
from src.services.slack_blocks import daily_report_message
from src.services.slack_client import SlackClient

logger = logging.getLogger(__name__)

WINDOW_BUFFER_MINUTES = 5


class DailyReportJob:
    def __init__(
        self,
        jira: IssueSource,
        slack: SlackClient,
        database: Database,
        project_key: str,
        timezone_name: str,
        critical_priorities: set[str],
        top_assignee_count: int = 5,
        extra_jql: str = "",
    ) -> None:
        self.jira = jira
        self.slack = slack
        self.database = database
        self.project_key = project_key
        self.tz = ZoneInfo(timezone_name)
        self.critical_priorities = critical_priorities
        self.top_assignee_count = top_assignee_count
        self.extra_jql = extra_jql

    def run(self, now: datetime | None = None, force: bool = False) -> DailyReport | None:
        now_local = (now or datetime.now(self.tz)).astimezone(self.tz)
        day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        with self.database.session_scope() as session:
            already_sent = ReportRepository(session).was_sent(day_start.date())
        if already_sent and not force:
            logger.info("Daily report for %s already sent; skipping.", day_start.date())
            return None

        report = compute_daily_report(
            issues=self.jira.search_issues(self._build_jql(now_local, day_start)),
            window_start=day_start,
            window_end=day_end,
            critical_priorities=self.critical_priorities,
            top_n=self.top_assignee_count,
        )

        self.slack.send(daily_report_message(report, self.project_key))

        if not already_sent:
            with self.database.session_scope() as session:
                ReportRepository(session).record(report)

        logger.info(
            "Daily report sent: opened=%d closed=%d open_critical=%d",
            len(report.created), len(report.closed), len(report.open_critical),
        )
        return report

    def _build_jql(self, now_local: datetime, day_start: datetime) -> str:
        # Relative minutes avoid depending on the Jira user's profile timezone;
        # the exact day window is applied afterwards in compute_daily_report.
        minutes = math.ceil((now_local - day_start).total_seconds() / 60) + WINDOW_BUFFER_MINUTES
        return build_jql(
            self.project_key,
            f"created >= -{minutes}m OR resolved >= -{minutes}m OR statusCategory != Done",
            extra=self.extra_jql,
            order_by="priority DESC, created ASC",
        )
