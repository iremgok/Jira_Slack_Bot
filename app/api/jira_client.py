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

    def search_issue(self, jql: str, max_results: int = 50) -> dict[str, Any]:
        """
        Search Jira issues using jql
        """

        logger.info(f"Requesting issues from jira...")

        try:

            response = self.client.get(
                "/rest/api/3/search",
                params={
                    "jql": jql,
                    "maxResults": max_results,
                },
            )

        except httpx.HTTPError as error:

            raise JiraConnectionError(
                "Failed to connect to Jira."
            ) from error

        response.raise_for_status()
        logger.info("Issues received successfully")

        return response.json()


    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """"
        Retreive a single jira issue
        """

        logger.info(f"Fetching issue: {issue_key}")

        try:

            response = self.client.get(f"/rest/api/3/issue/{issue_key}",)

        except httpx.HTTPError as error:

            raise JiraConnectionError(
                "Failed to connect to Jira."
            ) from error

        response.raise_for_status()
        return response.json()


    def health_check(self) -> bool:
        """
        Check Jira API connectivity
        """

        try:
            response= self.client.get("/rest/api/3/myself")
            response.raise_for_status()
            logger.info("Successfully connected to JIRA")

            return True

        except httpx.HTTPError as exc:
            logger.info(f"Jira connection failed: {exc}")

            return False


    def close(self) -> None:
        """
        Close the HTTP Client
        """
        self.client.close()

