from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Central application configuration

    Loads environment variables from the .env file.
    and provides a single source of truth for all
    application settings.
    """

    # -------APP Configuration---------
    app_name: str = "Jira Slack Bot"
    app_env: str = "development"

    # -------JIRA Configuration---------
    jira_url: str = ""
    jira_email: str = ""
    jira_token: str = ""
    project_key: str = ""

    # -------SLACK Configuration---------
    slack_token: str = ""
    slack_channel: str = ""

    # -------DATABASE Configuration---------
    database_url: str = "sqlite:///jira_bot.db"

    # -------SCHEDULAR Configuration---------
    check_interval: int = 300

    # -------LOGGING Configuration---------
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = False,
        extra = "ignore"
    )

settings = Settings()

