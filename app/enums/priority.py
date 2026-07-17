from enum import Enum


class IssuePriority(str, Enum):
    """
    Supported jira issue priorities.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    HIGHEST = "Highest"
