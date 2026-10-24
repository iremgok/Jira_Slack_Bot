"""
Slack transport layer.

Delivers an already-built message (fallback text + Block Kit blocks) using
either an Incoming Webhook or the Web API ``chat.postMessage`` with a bot
token. Message *content* is built in ``slack_blocks.py``.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.exceptions import SlackError
from src.services.slack_blocks import SlackMessage

logger = logging.getLogger(__name__)

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
AUTH_TEST_URL = "https://slack.com/api/auth.test"


class SlackClient:
    def __init__(
        self,
        webhook_url: str = "",
        bot_token: str = "",
        channel: str = "",
        dry_run: bool = False,
        timeout: int = 10,
    ) -> None:
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel = channel
        self.dry_run = dry_run
        self.timeout = timeout

        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def send(self, message: SlackMessage) -> None:
        """Send a message; raises ``SlackError`` if delivery fails."""
        payload: dict[str, Any] = {"text": message.text, "blocks": message.blocks}

        if self.dry_run:
            logger.info("[DRY RUN] Slack message:\n%s", json.dumps(payload, ensure_ascii=False, indent=2))
            return
        if self.webhook_url:
            self._send_webhook(payload)
        else:
            self._send_bot(payload)

    def health_check(self) -> bool:
        if self.dry_run or not self.bot_token:
            return True  # webhooks have no side-effect-free health endpoint
        try:
            data = self._post_api(AUTH_TEST_URL, {})
            logger.info("Connected to Slack workspace '%s'.", data.get("team"))
            return True
        except SlackError as exc:
            logger.error("Slack health check failed: %s", exc)
            return False

    def close(self) -> None:
        self.session.close()

    # ------------------------------------------------------------------ #
    def _send_webhook(self, payload: dict[str, Any]) -> None:
        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SlackError(f"Could not reach Slack webhook: {exc}") from exc
        if not response.ok:
            raise SlackError(f"Slack webhook returned HTTP {response.status_code}: {response.text[:200]}")
        logger.info("Slack message sent via webhook.")

    def _send_bot(self, payload: dict[str, Any]) -> None:
        data = self._post_api(POST_MESSAGE_URL, {**payload, "channel": self.channel})
        logger.info("Slack message sent to %s (ts=%s).", self.channel, data.get("ts"))

    def _post_api(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = response.json()
        except requests.RequestException as exc:
            raise SlackError(f"Could not reach Slack API: {exc}") from exc
        except ValueError as exc:
            raise SlackError(f"Slack API returned non-JSON (HTTP {response.status_code})") from exc

        # Slack Web API returns HTTP 200 with ok=false on logical errors
        if not data.get("ok"):
            raise SlackError(f"Slack API error: {data.get('error', 'unknown_error')}")
        return data
