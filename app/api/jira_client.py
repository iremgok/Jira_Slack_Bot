from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config.settings import settings
from app.utils.logger import logger


class JiraClient:
    """
    Jira responsible for communicating with Jira Rest API
    """

    def __init__(self) -> None:
        self.base_url = settings.jira_url
        self.project_key = settings.project_key

        self.client = httpx.Client(
            base_url = self.base_url,
            auth = (settings.jira_email, settings.jira_token),
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )


    @retry(
        stop = stop_after_attempt(3),
        wait = wait_fixed(2)
    )

    def search_issue(self, jql: str) -> dict[str, Any]:
        """
        Search Jira issues using jql
        """

        logger.info(f"")












