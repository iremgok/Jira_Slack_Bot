"""
Periodic job: detect new / updated Jira issues and notify Slack.

Flow per run:
  1. Work out how far back to look (since the last *successful* run).
  2. Fetch recently updated issues from Jira.
  3. Compare each with its stored snapshot -> new / changed / unchanged.
  4. Notify Slack, then store the new snapshot (so a failed send is retried).
  5. Advance the cursor only if every notification was delivered.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.exceptions import BotError
from src.database.db import Database
from src.database.repository import IssueRepository, JobStateRepository
from src.models.issue import JiraIssue, detect_changes
from src.services.jira_client import IssueSource, build_jql
from src.services.slack_blocks import SlackMessage, new_issue_message, updated_issue_message
from src.services.slack_client import SlackClient

logger = logging.getLogger(__name__)

CURSOR_KEY = "issue_poller.last_success"
CLOCK_SKEW_BUFFER_MINUTES = 2


@dataclass
class PollResult:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    failed: int = 0


class IssuePoller:
    def __init__(
        self,
        jira: IssueSource,
        slack: SlackClient,
        database: Database,
        project_key: str,
        extra_jql: str = "",
        initial_lookback_minutes: int = 60,
    ) -> None:
        self.jira = jira
        self.slack = slack
        self.database = database
        self.project_key = project_key
        self.extra_jql = extra_jql
        self.initial_lookback_minutes = initial_lookback_minutes

    def run(self) -> PollResult:
        started_at = datetime.now(timezone.utc)
        result = PollResult()

        with self.database.session_scope() as session:
            last_success = JobStateRepository(session).get_datetime(CURSOR_KEY)

        lookback = self._lookback_minutes(last_success, started_at)
        jql = build_jql(
            self.project_key,
            f"updated >= -{lookback}m",
            extra=self.extra_jql,
            order_by="updated ASC",
        )
        issues = self.jira.search_issues(jql)
        result.fetched = len(issues)

        with self.database.session_scope() as session:
            snapshots = IssueRepository(session).get_snapshots([i.key for i in issues])

        for issue in issues:
            self._handle_issue(issue, snapshots.get(issue.key), result)

        if result.failed == 0:
            with self.database.session_scope() as session:
                JobStateRepository(session).set_datetime(CURSOR_KEY, started_at)
        else:
            logger.warning("%d notification(s) failed; cursor not advanced, will retry.", result.failed)

        logger.info(
            "Poll finished: fetched=%d new=%d updated=%d failed=%d (lookback=%dm)",
            result.fetched, result.new, result.updated, result.failed, lookback,
        )
        return result

    # ------------------------------------------------------------------ #
    def _handle_issue(self, issue: JiraIssue, previous: JiraIssue | None, result: PollResult) -> None:
        message: SlackMessage | None = None

        if previous is None:
            message = new_issue_message(issue)
            result.new += 1
        elif issue.updated > previous.updated:
            changes = detect_changes(previous, issue)
            if changes:
                message = updated_issue_message(issue, changes)
                result.updated += 1
            else:
                logger.debug("%s updated without tracked field changes.", issue.key)
        else:
            return  # already processed this version

        try:
            if message is not None:
                self.slack.send(message)
            with self.database.session_scope() as session:
                IssueRepository(session).upsert(issue)
        except BotError as exc:
            result.failed += 1
            logger.error("Could not process %s: %s", issue.key, exc)

    def _lookback_minutes(self, last_success: datetime | None, now: datetime) -> int:
        if last_success is None:
            return self.initial_lookback_minutes
        elapsed = (now - last_success).total_seconds() / 60
        return max(1, math.ceil(elapsed)) + CLOCK_SKEW_BUFFER_MINUTES
