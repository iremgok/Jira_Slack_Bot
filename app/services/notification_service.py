from __future__ import annotations

from typing import Any

from app.api.slack_client import SlackClient
from app.models.issue import Issue
from app.repositories.notification_repository import NotificationRepository
from app.utils.logger import logger
from app.utils.formatter import (
    build_new_issue_message,
    build_updated_issue_message,
    build_error_message,
)


class NotificationService:
    """
    Service responsible for sending formatted Slack notifications and logging results.
    """

    def __init__(
        self,
        slack_client: SlackClient,
        repository: NotificationRepository | None = None,
    ) -> None:
        self.slack_client = slack_client
        self.repository = repository

    def send_new_issue(self, issue: Issue) -> bool:
        """
        Send notification for a newly created Jira issue and log it.
        """
        text_message, blocks = build_new_issue_message(issue)
        success = False
        error_message = None

        logger.info(f"Sending Block Kit notification for new issue {issue.issue_key}.")
        try:
            success = self.slack_client.send_message(message=text_message, blocks=blocks)
        except Exception as exc:
            error_message = str(exc)
            logger.error(f"Error sending new issue notification: {exc}")
            raise exc
        finally:
            if self.repository:
                try:
                    self.repository.create_log(
                        issue_key=issue.issue_key,
                        notification_type="new",
                        success=success,
                        error_message=error_message,
                    )
                except Exception as log_exc:
                    logger.error(f"Failed to record notification log to database: {log_exc}")

        return success

    def send_issue_updated(self, issue: Issue, changes: list[str]) -> bool:
        """
        Send notification when an issue is updated, showing tracked changes.
        """
        text_message, blocks = build_updated_issue_message(issue, changes)
        success = False
        error_message = None

        logger.info(f"Sending Block Kit update notification for {issue.issue_key}.")
        try:
            success = self.slack_client.send_message(message=text_message, blocks=blocks)
        except Exception as exc:
            error_message = str(exc)
            logger.error(f"Error sending update notification: {exc}")
            raise exc
        finally:
            if self.repository:
                try:
                    self.repository.create_log(
                        issue_key=issue.issue_key,
                        notification_type="updated",
                        success=success,
                        error_message=error_message,
                    )
                except Exception as log_exc:
                    logger.error(f"Failed to record notification log to database: {log_exc}")

        return success

    def send_error(self, error_message: str) -> bool:
        """
        Send error notification to Slack.
        """
        text_message, blocks = build_error_message(error_message)
        success = False
        logger.error(f"Sending bot error notification: {error_message}")
        try:
            success = self.slack_client.send_message(message=text_message, blocks=blocks)
        except Exception as exc:
            logger.error(f"Error sending error notification: {exc}")
            raise exc
        return success

    def send_message(self, message: str, blocks: list[dict[str, Any]] | None = None) -> bool:
        """
        Send a generic Slack message, optionally with Block Kit blocks.
        """
        logger.info("Sending generic Slack message.")
        return self.slack_client.send_message(message, blocks)
