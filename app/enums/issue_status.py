from enum import Enum


class IssueStatus(str, Enum):
    """
    Supported Jira issue Statues
    """

    TO_DO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    BLOCKED = "Blocked"
    DONE = "Done"