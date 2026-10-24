"""
Central, validated application configuration.

All secrets are read from environment variables (or a local ``.env`` file)
and never hardcoded. Tokens are stored as ``SecretStr`` so they are not
accidentally printed in logs or tracebacks.
"""
from __future__ import annotations

from functools import lru_cache

from apscheduler.triggers.cron import CronTrigger
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
    str_strip_whitespace=True,
)


class DatabaseSettings(BaseSettings):
    """Only what database tooling (e.g. Alembic) needs - no API secrets required."""

    model_config = _ENV_CONFIG

    database_url: str = "sqlite:///jira_bot.db"
    # Run "alembic upgrade head" automatically on application startup
    db_auto_migrate: bool = True
    # How long to wait for the database to accept connections on startup
    db_connect_timeout_seconds: int = Field(default=60, ge=0)


class Settings(DatabaseSettings):
    model_config = _ENV_CONFIG

    # ---------- App ----------
    app_name: str = "Jira Slack Bot"
    timezone: str = "Europe/Istanbul"

    # ---------- Jira ----------
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_project_key: str = ""
    # Optional extra JQL clause, e.g. "sprint in openSprints()"
    jira_extra_jql: str = ""
    jira_timeout_seconds: int = Field(default=30, ge=1)
    # Serve bundled sample data instead of calling Jira (local development)
    jira_mock_mode: bool = False

    # ---------- Slack ----------
    slack_webhook_url: SecretStr = SecretStr("")
    slack_bot_token: SecretStr = SecretStr("")
    slack_channel: str = ""
    # Log messages instead of sending them (local development)
    slack_dry_run: bool = False

    # ---------- Scheduler ----------
    poll_interval_seconds: int = Field(default=300, ge=30)
    initial_lookback_minutes: int = Field(default=60, ge=1)
    daily_report_cron: str = "0 18 * * *"

    # ---------- Report ----------
    critical_priorities: str = "Highest,High"
    top_assignee_count: int = Field(default=5, ge=1)

    # ---------- Logging ----------
    log_level: str = "INFO"
    log_dir: str = "logs"

    @field_validator("jira_base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("JIRA_BASE_URL must start with http:// or https://")
        return value

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid LOG_LEVEL: {value}")
        return value

    @field_validator("daily_report_cron")
    @classmethod
    def _validate_cron(cls, value: str) -> str:
        try:
            CronTrigger.from_crontab(value)
        except ValueError as exc:
            raise ValueError(f"Invalid DAILY_REPORT_CRON '{value}': {exc}") from exc
        return value

    @model_validator(mode="after")
    def _check_required_credentials(self) -> "Settings":
        missing: list[str] = []

        if not self.jira_base_url:
            missing.append("JIRA_BASE_URL")  # needed for browse links even in mock mode
        if not self.jira_project_key:
            missing.append("JIRA_PROJECT_KEY")
        if not self.jira_mock_mode:
            if not self.jira_email:
                missing.append("JIRA_EMAIL")
            if not self.jira_api_token.get_secret_value():
                missing.append("JIRA_API_TOKEN")

        if not self.slack_dry_run:
            has_webhook = bool(self.slack_webhook_url.get_secret_value())
            has_token = bool(self.slack_bot_token.get_secret_value())
            if not has_webhook and not has_token:
                missing.append("SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN")
            if has_token and not has_webhook and not self.slack_channel:
                missing.append("SLACK_CHANNEL")

        if missing:
            raise ValueError("Missing required configuration: " + ", ".join(missing))
        return self

    @property
    def critical_priority_set(self) -> set[str]:
        return {p.strip().lower() for p in self.critical_priorities.split(",") if p.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance (loaded once per process)."""
    return Settings()
