from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Loads environment variables from the .env file
    and provides a single source of truth for all
    application settings.
    """

    # -------------------------
    # Jira Configuration
    # -------------------------
    jira_url: str = ""
    jira_email: str = ""
    jira_token: str = ""

    # -------------------------
    # Slack Configuration
    # -------------------------
    slack_token: str = ""
    slack_channel: str = ""

    # -------------------------
    # Database Configuration
    # -------------------------
    database_url: str = "sqlite:///jira_bot.db"

    # -------------------------
    # Scheduler Configuration
    # -------------------------
    check_interval: int = 300

    # -------------------------
    # Logging Configuration
    # -------------------------
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()