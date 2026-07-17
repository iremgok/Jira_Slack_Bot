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