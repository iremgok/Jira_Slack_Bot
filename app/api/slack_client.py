from __future__ import annotations

from typing import Any
import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config.settings import settings
from app.exceptions.custom_exceptions import SlackConnectionError, ConfigurationError
from app.utils.logger import logger


class SlackClient:
    """
    Client responsible for communicating with the Slack API or Webhook.
    """

    def __init__(self) -> None:
        self.webhook_url = settings.slack_webhook_url
        self.token = settings.slack_token
        self.channel = settings.slack_channel

        self.web_client = None
        if self.token:
            self.web_client = WebClient(token=self.token)

        # Validate configuration
        if not self.webhook_url and not self.token:
            raise ConfigurationError(
                "Either SLACK_WEBHOOK_URL or SLACK_TOKEN must be configured in environment."
            )
        if self.token and not self.channel:
            raise ConfigurationError(
                "SLACK_CHANNEL must be configured when SLACK_TOKEN is provided."
            )

    def send_message(self, message: str, blocks: list[dict[str, Any]] | None = None) -> bool:
        """
        Send a message to Slack using Webhook or WebClient.
        """
        if self.webhook_url:
            return self._send_via_webhook(message, blocks)
        elif self.web_client:
            return self._send_via_web_client(message, blocks)
        return False

    def _send_via_webhook(self, message: str, blocks: list[dict[str, Any]] | None = None) -> bool:
        """
        Send message to Slack Webhook URL.
        """
        logger.info("Sending message via Slack Webhook...")
        payload: dict[str, Any] = {"text": message}
        if blocks:
            payload["blocks"] = blocks

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info("Message successfully sent via Webhook.")
            return True
        except httpx.HTTPError as exc:
            logger.error(f"Failed to send Slack Webhook message: {exc}")
            raise SlackConnectionError("Failed to connect to Slack Webhook API.") from exc

    def _send_via_web_client(self, message: str, blocks: list[dict[str, Any]] | None = None) -> bool:
        """
        Send message to Slack via WebClient.
        """
        logger.info(f"Sending message via Slack WebClient to channel: {self.channel}")
        try:
            response = self.web_client.chat_postMessage(
                channel=self.channel,
                text=message,
                blocks=blocks,
            )
            logger.info(f"Message successfully sent via WebClient. TS: {response['ts']}")
            return True
        except SlackApiError as exc:
            error_detail = exc.response.get("error", "Unknown WebClient Error")
            logger.error(f"Failed to send Slack WebClient message: {error_detail}")
            raise SlackConnectionError(error_detail) from exc

    def health_check(self) -> bool:
        """
        Check Slack connectivity.
        """
        if self.web_client:
            try:
                self.web_client.auth_test()
                logger.info("Successfully connected to Slack via WebClient")
                return True
            except SlackApiError as exc:
                logger.error(f"Slack WebClient auth_test failed: {exc.response['error']}")
                return False
        elif self.webhook_url:
            try:
                # Basic connection test
                with httpx.Client(timeout=5.0) as client:
                    # Parsing host URL to verify connection
                    parsed_url = httpx.URL(self.webhook_url)
                    ping_url = f"{parsed_url.scheme}://{parsed_url.host}"
                    res = client.get(ping_url)
                logger.info(f"Slack Webhook host ({ping_url}) is reachable.")
                return True
            except httpx.HTTPError as exc:
                logger.error(f"Slack Webhook reachability test failed: {exc}")
                return False
        return False
