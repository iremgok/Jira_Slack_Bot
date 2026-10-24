"""Application-specific exception hierarchy."""


class BotError(Exception):
    """Base class for all bot errors."""


class JiraError(BotError):
    """Raised when the Jira API cannot be reached or returns an error."""


class JiraAuthError(JiraError):
    """Raised when Jira rejects the credentials (401/403)."""


class SlackError(BotError):
    """Raised when a Slack message cannot be delivered."""


class RepositoryError(BotError):
    """Raised when a database operation fails."""
