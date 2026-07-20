from __future__ import annotations

from app.api.slack_client import SlackClient
from app.models.issue import Issue
from app.utils.logger import logger


class NotificationService:
    """
    Service responsible for sending Slack notifications.
    """

    def __init__(self, slack_client: SlackClient) -> None:
        self.slack_client = slack_client

    def send_new_issue(self, issue: Issue) -> bool:
        """
        Send notification for a newly created Jira issue.
        """

        message = (
            "🔔 *New Jira Issue*\n\n"
            f"*Key:* {issue.issue_key}\n"
            f"*Summary:* {issue.summary}\n"
            f"*Status:* {issue.status.value}\n"
            f"*Priority:* {issue.priority.value}\n"
            f"*Assignee:* {issue.assignee or 'Unassigned'}"
        )

        logger.info(
            f"Sending notification for issue {issue.issue_key}."
        )

        return self.slack_client.send_message(message)

    def send_issue_updated(self, issue: Issue) -> bool:
        """
        Send notification when an issue is updated.
        """

        message = (
            "✏️ *Jira Issue Updated*\n\n"
            f"*Key:* {issue.issue_key}\n"
            f"*Summary:* {issue.summary}\n"
            f"*Status:* {issue.status.value}\n"
            f"*Priority:* {issue.priority.value}"
        )

        logger.info(
            f"Sending update notification for {issue.issue_key}."
        )

        return self.slack_client.send_message(message)

    def send_error(self, error_message: str) -> bool:
        """
        Send error notification to Slack.
        """

        message = (
            "🚨 *Jira Bot Error*\n\n"
            f"{error_message}"
        )

        logger.error(error_message)

        return self.slack_client.send_message(message)
