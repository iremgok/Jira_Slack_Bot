from app.enums.issue_status import IssueStatus
from app.enums.priority import IssuePriority
from app.utils.helpers import parse_status, parse_priority


def test_parse_status():
    assert parse_status("In Progress") == IssueStatus.IN_PROGRESS
    assert parse_status("backlog") == IssueStatus.TO_DO
    assert parse_status("unknown status") == IssueStatus.TO_DO
    assert parse_status("Done") == IssueStatus.DONE
    assert parse_status("Resolved") == IssueStatus.DONE


def test_parse_priority():
    assert parse_priority("Highest") == IssuePriority.HIGHEST
    assert parse_priority("Critical") == IssuePriority.HIGHEST
    assert parse_priority("Medium") == IssuePriority.MEDIUM
    assert parse_priority("unknown priority") == IssuePriority.MEDIUM
