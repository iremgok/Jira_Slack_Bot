import pytest
from pydantic import ValidationError

from src.core.config import Settings

BASE = {"jira_base_url": "https://x.atlassian.net", "jira_project_key": "KAN", "_env_file": None}


def test_missing_credentials_are_reported():
    with pytest.raises(ValidationError, match="JIRA_EMAIL.*JIRA_API_TOKEN.*SLACK_WEBHOOK_URL"):
        Settings(**BASE)


def test_mock_and_dry_run_need_no_secrets():
    settings = Settings(**BASE, jira_mock_mode=True, slack_dry_run=True)
    assert settings.critical_priority_set == {"highest", "high"}


def test_invalid_cron_rejected():
    with pytest.raises(ValidationError, match="DAILY_REPORT_CRON"):
        Settings(**BASE, jira_mock_mode=True, slack_dry_run=True, daily_report_cron="99 99 * * *")


def test_tokens_are_not_exposed_in_repr():
    settings = Settings(**BASE, jira_email="a@b.c", jira_api_token="secret-token",
                        slack_webhook_url="https://hooks.slack.com/x")
    assert "secret-token" not in repr(settings)
