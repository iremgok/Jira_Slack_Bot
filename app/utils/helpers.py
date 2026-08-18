from datetime import UTC, datetime

from app.enums.issue_status import IssueStatus
from app.enums.priority import IssuePriority
from app.utils.logger import logger


def parse_datetime(dt_str: str) -> datetime:
    """
    Parse ISO 8601 string from Jira safely into UTC datetime.
    """
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        try:
            # Fallback format parsing
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            logger.error(f"Failed to parse datetime string: {dt_str}. Using current time.")
            dt = datetime.now(UTC)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_datetime(dt: datetime) -> datetime:
    """
    Normalize datetime object to UTC aware datetime.
    """
    if dt is None:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_status(name: str) -> IssueStatus:
    """
    Safely convert status string to IssueStatus enum, defaulting to TO_DO.
    """
    for status in IssueStatus:
        if status.value.lower() == name.lower():
            return status

    # Safe mappings for common status names
    name_lower = name.lower()
    if name_lower in ["backlog", "selected for development", "open", "new", "to do"]:
        return IssueStatus.TO_DO
    if name_lower in ["in progress", "developing", "dev", "active"]:
        return IssueStatus.IN_PROGRESS
    if name_lower in ["in review", "peer review", "qa", "testing", "under review"]:
        return IssueStatus.IN_REVIEW
    if name_lower in ["blocked", "on hold", "waiting"]:
        return IssueStatus.BLOCKED
    if name_lower in ["done", "closed", "resolved", "completed"]:
        return IssueStatus.DONE

    logger.warning(f"Unknown status '{name}' from Jira, falling back to TO_DO.")
    return IssueStatus.TO_DO


def parse_priority(name: str) -> IssuePriority:
    """
    Safely convert priority string to IssuePriority enum, defaulting to MEDIUM.
    """
    for p in IssuePriority:
        if p.value.lower() == name.lower():
            return p

    # Safe mappings for common priority names
    name_lower = name.lower()
    if name_lower in ["highest", "critical", "blocker"]:
        return IssuePriority.HIGHEST
    if name_lower in ["high", "major"]:
        return IssuePriority.HIGH
    if name_lower in ["medium", "normal", "average", "default"]:
        return IssuePriority.MEDIUM
    if name_lower in ["low", "minor", "lowest", "trivial"]:
        return IssuePriority.LOW

    logger.warning(f"Unknown priority '{name}' from Jira, falling back to MEDIUM.")
    return IssuePriority.MEDIUM
