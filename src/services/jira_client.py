"""
Jira REST API client.

Only responsible for talking HTTP to Jira and turning responses into
``JiraIssue`` models. It uses the Jira Cloud ``/rest/api/3/search/jql``
endpoint with token-based pagination.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.exceptions import JiraAuthError, JiraError
from src.models.issue import JIRA_FIELDS, JiraIssue

logger = logging.getLogger(__name__)

SEARCH_ENDPOINT = "/rest/api/3/search/jql"
MYSELF_ENDPOINT = "/rest/api/3/myself"
PAGE_SIZE = 100


class IssueSource(Protocol):
    """Anything that can return issues for a JQL query (real client or mock)."""

    def search_issues(self, jql: str, limit: int | None = None) -> list[JiraIssue]: ...

    def close(self) -> None: ...


def build_jql(project_key: str, *conditions: str, extra: str = "", order_by: str = "") -> str:
    """Compose a JQL query scoped to a project, with optional extra filters."""
    clauses = [f'project = "{project_key}"']
    clauses.extend(f"({c})" for c in (*conditions, extra) if c)
    jql = " AND ".join(clauses)
    return f"{jql} ORDER BY {order_by}" if order_by else jql


class JiraClient:
    """Thin, resilient wrapper around the Jira REST API."""

    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})

        # Retry transient failures (rate limiting / server errors), honouring Retry-After
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def search_issues(self, jql: str, limit: int | None = None) -> list[JiraIssue]:
        """Run a JQL query and return all matching issues (follows pagination)."""
        logger.info("Searching Jira issues: %s", jql)
        issues: list[JiraIssue] = []
        next_token: str | None = None

        while True:
            params: dict[str, Any] = {"jql": jql, "fields": JIRA_FIELDS, "maxResults": PAGE_SIZE}
            if next_token:
                params["nextPageToken"] = next_token

            data = self._get(SEARCH_ENDPOINT, params=params)
            issues.extend(self._parse_issues(data.get("issues", [])))

            next_token = data.get("nextPageToken")
            if data.get("isLast", True) or not next_token:
                break
            if limit is not None and len(issues) >= limit:
                break

        if limit is not None:
            issues = issues[:limit]
        logger.info("Fetched %d issue(s) from Jira.", len(issues))
        return issues

    def health_check(self) -> bool:
        try:
            self._get(MYSELF_ENDPOINT)
            return True
        except JiraError as exc:
            logger.error("Jira health check failed: %s", exc)
            return False

    def close(self) -> None:
        self.session.close()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise JiraError(f"Jira request timed out after {self.timeout}s: {path}") from exc
        except requests.RequestException as exc:
            raise JiraError(f"Could not reach Jira at {self.base_url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise JiraAuthError(
                f"Jira rejected the credentials (HTTP {response.status_code}). "
                "Check JIRA_EMAIL / JIRA_API_TOKEN and project permissions."
            )
        if response.status_code == 400:
            raise JiraError(f"Invalid Jira request: {self._error_detail(response)}")
        if not response.ok:
            raise JiraError(
                f"Jira returned HTTP {response.status_code} for {path}: "
                f"{self._error_detail(response)}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise JiraError(f"Jira returned a non-JSON response for {path}") from exc

    def _parse_issues(self, raw_issues: list[dict[str, Any]]) -> list[JiraIssue]:
        parsed: list[JiraIssue] = []
        for raw in raw_issues:
            try:
                parsed.append(JiraIssue.from_api(raw, self.base_url))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed issue %s: %s", raw.get("key", "?"), exc)
        return parsed

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300]
        messages = body.get("errorMessages") or []
        errors = body.get("errors") or {}
        detail = "; ".join([*messages, *(f"{k}: {v}" for k, v in errors.items())])
        return detail or response.text[:300]
