from __future__ import annotations

from app.exceptions.custom_exceptions import (
    DatabaseError,
    JiraConnectionError,
    RepositoryError,
    SlackConnectionError,
)
from app.utils.logger import logger


class ExceptionHandler:
    """
    Centralized exception handling.
    """

    @staticmethod
    def handle(
        exception: Exception,
        notification_service=None,
    ) -> None:
        """
        Handle application exceptions.
        """

        if isinstance(exception, JiraConnectionError):
            logger.error(f"Jira Error: {exception}")

        elif isinstance(exception, SlackConnectionError):
            logger.error(f"Slack Error: {exception}")

        elif isinstance(exception, RepositoryError):
            logger.error(f"Repository Error: {exception}")

        elif isinstance(exception, DatabaseError):
            logger.error(f"Database Error: {exception}")

        else:
            logger.exception(exception)

        if notification_service is not None:
            try:
                notification_service.send_error(str(exception))
            except Exception as e:
                logger.error(f"Failed to send error notification to Slack: {e}")
