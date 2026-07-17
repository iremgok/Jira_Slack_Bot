from __future__ import annotations

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config.settings import settings
from app.utils.logger import logger


class SlackClient:
    """
    Client responsible for communicating with the Slack API
    """

    def __init__(self) -> None:
        self.client = WebClient(token=settings.slack_token)
        self.channel = settings.slack_channel


    def send_message(self, message: str) -> bool:
        """
        Send a message to the configured Slack Channel
        """

        try:
            response = self.client.chat_postMessage(
                channel = self.channel,
                text = message,
            )

            logger.info(
                f"Message succesfully sent to Slack. Timestamp: {response['ts']}"
            )

            return True

        except SlackApiError as exc:
            logger.error(
                f"Failed to send Slack Message: {exc.response['error']}"
            )

            return False

    def health_check(self) -> bool:
        """
        Check Slack API connectivity.
        """

        try:
            self.client.auth_test()
            logger.info("Successfully connected to Slack")

            return True

        except SlackApiError as exc:
            logger.error(
                f"Failed to connect to Slack API: {exc.response['error']}"
            )

            return False
