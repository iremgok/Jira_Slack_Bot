from enum import Enum


class IssueStatus(str, Enum):
    """
    Supported Jira issue Statues
    """

    TO_DO = "To Do",
    IN_PROGRESS = "In Progress",
    DONE = "Done",
    BLOCKED = "Blocked"