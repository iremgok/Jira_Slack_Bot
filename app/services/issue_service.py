from __future__ import annotations

from app.api.jira_client import JiraClient
from app.repositories.issue_repository import IssueRepository
from app.models.issue import Issue
from app.utils.logger import logger
from app.services.notification_service import NotificationService
from app.utils.helpers import (
    parse_datetime,
    normalize_datetime,
    parse_status,
    parse_priority,
)


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

    def sync_issues(self) -> None:
        """
        Fetch issues from Jira and synchronize them with database.
        """
        logger.info("Starting Jira synchronization...")

        jql = f"project = '{self.jira_client.project_key}' ORDER BY updated DESC"
        try:
            # Retrieve all issues (paginated automatically)
            issues = self.jira_client.search_issues(jql)
            logger.info(f"{len(issues)} issue(s) received from Jira.")

            for jira_issue in issues:
                try:
                    self.process_issue(jira_issue)
                except Exception as issue_error:
                    logger.error(f"Error processing issue {jira_issue.get('key')}: {issue_error}")

            logger.info("Synchronization completed successfully.")
        except Exception as sync_error:
            logger.error(f"Error occurred during Jira sync: {sync_error}")
            raise sync_error

    def process_issue(self, jira_issue: dict) -> None:
        """
        Process a single Jira issue: Create if new, Update if updated_at changed.
        """
        issue_key = jira_issue["key"]
        mapped_issue = self.map_issue(jira_issue)

        existing_issue = self.repository.get_by_key(issue_key)

        if existing_issue is None:
            # Create in database
            self.repository.create(mapped_issue)
            # Notify Slack about new issue
            self.notification_service.send_new_issue(mapped_issue)
        else:
            # Normalize datetimes to UTC before comparison
            existing_updated = normalize_datetime(existing_issue.updated_at)
            mapped_updated = normalize_datetime(mapped_issue.updated_at)

            if mapped_updated > existing_updated:
                logger.info(f"Update detected for issue {issue_key}. Processing changes...")
                
                # Check what changed
                changes: list[str] = []
                if existing_issue.status != mapped_issue.status:
                    changes.append(f"*Status:* `{existing_issue.status.value}` ➡️ `{mapped_issue.status.value}`")
                if existing_issue.priority != mapped_issue.priority:
                    changes.append(f"*Priority:* `{existing_issue.priority.value}` ➡️ `{mapped_issue.priority.value}`")
                if existing_issue.assignee != mapped_issue.assignee:
                    old_assignee = existing_issue.assignee or "Unassigned"
                    new_assignee = mapped_issue.assignee or "Unassigned"
                    changes.append(f"*Assignee:* `{old_assignee}` ➡️ `{new_assignee}`")
                if existing_issue.summary != mapped_issue.summary:
                    changes.append(f"*Summary:* '{existing_issue.summary}' ➡️ '{mapped_issue.summary}'")

                # Update local database fields
                existing_issue.summary = mapped_issue.summary
                existing_issue.status = mapped_issue.status
                existing_issue.priority = mapped_issue.priority
                existing_issue.assignee = mapped_issue.assignee
                existing_issue.updated_at = mapped_issue.updated_at
                existing_issue.processed = False  # Mark as unprocessed for future state reference

                self.repository.update(existing_issue)

                # Send Slack notification if notable fields changed
                if changes:
                    self.notification_service.send_issue_updated(existing_issue, changes)
                else:
                    logger.info(f"Issue {issue_key} metadata updated, but no tracked fields changed.")
            else:
                logger.debug(f"Issue {issue_key} is up-to-date in database.")

    @classmethod
    def map_issue(cls, jira_issue: dict) -> Issue:
        """
        Convert Jira issue JSON payload to local database Issue model.
        """
        fields = jira_issue["fields"]

        # Parse Datetimes safely
        created_str = fields.get("created")
        updated_str = fields.get("updated")

        created_at = parse_datetime(created_str) if created_str else parse_datetime("")
        updated_at = parse_datetime(updated_str) if updated_str else parse_datetime("")

        status_name = fields["status"]["name"]
        priority_name = fields.get("priority", {}).get("name", "Medium")

        assignee = None
        if fields.get("assignee"):
            assignee = fields["assignee"].get("displayName")

        return Issue(
            issue_key=jira_issue["key"],
            summary=fields["summary"],
            status=parse_status(status_name),
            priority=parse_priority(priority_name),
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            processed=False,
            inserted_at=parse_datetime(""),
        )
