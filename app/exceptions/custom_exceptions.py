class JiraConnectionError(Exception):
    """
    Raised when Jira API cannot be reached.
    """


class SlackConnectionError(Exception):
    """
    Raised when Slack API request fails.
    """


class RepositoryError(Exception):
    """
    Raised when repository operations fail.
    """


class DatabaseError(Exception):
    """
    Raised when a database connection or transaction fails.
    """


class ConfigurationError(Exception):
    """
    Raised when application configuration is invalid.
    """
