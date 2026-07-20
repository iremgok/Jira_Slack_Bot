from __future__ import annotations
from datetime import UTC, datetime

from app.api.jira_client import JiraClient
from app.api.slack_client import SlackClient
from app.repositories.issue_repository import IssueRepository
from app.enums.issue_status import IssueStatus
from app.enums.priority import IssuePriority
from app.models.issue import Issue
from app.utils.logger import logger
from app.services.notification_service import NotificationService


class IssueService:
    """
    Business logic responsible for synchronizing Jira issues.
    """

    def __init__(
            self,
            jira_client: JiraClient,
            repository: IssueRepository,
            notification_service: NotificationService,
    ) -> None:
        self.jira_client = jira_client
        self.repository = repository
        self.notification_service = notification_service

        def sync_issue(self) -> None:
            """
            Fetch issues from Jira and synchronize them with database.
            """
            logger.info("Starting Jira synchronization...")

            response = self.jira_client.search_issues(
                "project = KAN ORDER BY updated DESC"
            )

            issues = response.get("issues", [])
            logger.info(f"{len(issues)} issue(s) received.")

            for jira_issue in issues:
                self.process_issue(jira_issue)

            logger.info("Synchronization completed.")


        def process_issue(self, jira_issue: dict) -> None:
            """
            Process a single Jira issue.
            """

            issue_key = jira_issue["key"]

            if self.repository.issue_exists(issue_key):
                logger.info(f"{issue_key} already exists.")
                return

            issue = self.map_issue(jira_issue)
            self.repository.create(issue)
            self.notification_service.send_new_issue(issue)

        @staticmethod
        def map_issue(jira_issue: dict) -> Issue:
            """
            Convert Jira JSON into Issue entity.
            """

            fields = jira_issue["fields"]

            return Issue(

                issue_key=jira_issue["key"],

                summary=fields["summary"],

                status=IssueStatus(fields["status"]["name"]),

                priority=IssuePriority(
                    fields["priority"]["name"]
                ),

                assignee=(
                    fields["assignee"]["displayName"]
                    if fields["assignee"]
                    else None
                ),

                created_at=datetime.fromisoformat(
                    fields["created"].replace("Z", "+00:00")
                ),

                updated_at=datetime.fromisoformat(
                    fields["updated"].replace("Z", "+00:00")
                ),

                processed=False,

                inserted_at=datetime.now(UTC),
            )

        def notify_new_issue(
                self,
                issue: Issue,
        ) -> None:
            """
            Notify Slack about a new issue.
            """

            message = (
                f"🔔 New Jira Issue\n\n"
                f"Key: {issue.issue_key}\n"
                f"Summary: {issue.summary}\n"
                f"Status: {issue.status.value}\n"
                f"Priority: {issue.priority.value}\n"
                f"Assignee: {issue.assignee}"
            )

            self.slack_client.send_message(message)
