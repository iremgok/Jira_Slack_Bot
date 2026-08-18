from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config.settings import settings
from app.exceptions.custom_exceptions import JiraConnectionError
from app.utils.logger import logger


class JiraClient:
    """
    Jira client responsible for communicating with Jira REST API.
    """

    def __init__(self) -> None:
        # Strip any accidental whitespace from URL
        self.base_url = settings.jira_url.rstrip("/")
        self.project_key = settings.project_key

        self.client = httpx.Client(
            base_url=self.base_url,
            auth=(settings.jira_email, settings.jira_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2)
    )
    def search_issue(self, jql: str, max_results: int = 50) -> dict[str, Any]:
        """
        Search Jira issues using JQL (returns a single page response).
        """
        logger.info(f"Requesting single page of issues from Jira with JQL: {jql}")

        try:
            response = self.client.get(
                "/rest/api/3/search",
                params={
                    "jql": jql,
                    "maxResults": max_results,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise JiraConnectionError("Failed to connect to Jira.") from error

        logger.info("Issues page received successfully.")
        return response.json()

    def search_issues(self, jql: str, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Search Jira issues using JQL and handle pagination.
        Returns a complete list of issue dicts.
        """
        all_issues: list[dict[str, Any]] = []
        start_at = 0
        max_results = 50

        logger.info(f"Starting paginated JQL search: '{jql}'")

        while True:
            logger.info(f"Fetching issues at offset {start_at}...")
            try:
                response = self.client.get(
                    "/rest/api/3/search",
                    params={
                        "jql": jql,
                        "startAt": start_at,
                        "maxResults": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as error:
                raise JiraConnectionError("Failed to connect to Jira during paginated search.") from error

            issues = data.get("issues", [])
            all_issues.extend(issues)

            total = data.get("total", 0)
            logger.info(f"Retrieved {len(issues)} issues in this page. Total matching: {total}.")

            start_at += len(issues)
            if start_at >= total or len(issues) < max_results or (limit is not None and len(all_issues) >= limit):
                break

        if limit is not None:
            all_issues = all_issues[:limit]

        logger.info(f"Total issues fetched from Jira: {len(all_issues)}")
        return all_issues

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """
        Retrieve a single Jira issue.
        """
        logger.info(f"Fetching issue: {issue_key}")

        try:
            response = self.client.get(f"/rest/api/3/issue/{issue_key}")
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise JiraConnectionError(f"Failed to connect to Jira for issue {issue_key}.") from error

        return response.json()

    def health_check(self) -> bool:
        """
        Check Jira API connectivity.
        """
        try:
            response = self.client.get("/rest/api/3/myself")
            response.raise_for_status()
            logger.info("Successfully connected to JIRA")
            return True
        except httpx.HTTPError as exc:
            logger.error(f"Jira connection failed: {exc}")
            return False

    def close(self) -> None:
        """
        Close the HTTP client.
        """
        self.client.close()
