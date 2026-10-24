from datetime import timedelta, timezone

from src.models.issue import detect_changes
from src.models.report import compute_daily_report
from tests.conftest import BASE_URL, NOW, make_issue


def test_from_api_parses_fields_and_link():
    issue = make_issue("KAN-7", status="In Progress", category="indeterminate", priority="High")
    assert issue.key == "KAN-7"
    assert issue.status == "In Progress"
    assert issue.url == f"{BASE_URL}/browse/KAN-7"
    assert issue.created == NOW and issue.created.tzinfo == timezone.utc
    assert not issue.is_done
    assert issue.is_critical({"highest", "high"})


def test_from_api_handles_missing_optional_fields():
    issue = make_issue(assignee=None)
    assert issue.assignee is None
    assert issue.assignee_display == "Unassigned"


def test_detect_changes_reports_only_tracked_fields():
    old = make_issue(status="To Do", assignee="Ayşe")
    new = make_issue(status="Done", category="done", assignee=None, updated=NOW + timedelta(hours=1))
    changes = {c.field: (c.old, c.new) for c in detect_changes(old, new)}
    assert changes == {"Status": ("To Do", "Done"), "Assignee": ("Ayşe", "Unassigned")}


def test_compute_daily_report():
    start = NOW.replace(hour=0)
    end = start + timedelta(days=1)
    yesterday = start - timedelta(days=1)
    issues = [
        make_issue("KAN-1", created=NOW, priority="Highest", assignee="Ali"),
        make_issue("KAN-2", created=yesterday, category="done", status="Done", resolved=NOW),
        make_issue("KAN-3", created=yesterday, priority="High", assignee="Ali"),
        make_issue("KAN-4", created=yesterday, priority="Low", assignee="Veli"),
        make_issue("KAN-5", created=yesterday - timedelta(days=3), category="done",
                   status="Done", resolved=yesterday),
    ]
    report = compute_daily_report(issues, start, end, {"highest", "high"}, top_n=2)

    assert [i.key for i in report.created] == ["KAN-1"]
    assert [i.key for i in report.closed] == ["KAN-2"]
    assert [i.key for i in report.open_critical] == ["KAN-3", "KAN-1"]
    assert [(a.name, a.open_issues) for a in report.top_assignees] == [("Ali", 2), ("Veli", 1)]
    assert report.total_open == 3


def test_closed_without_resolution_uses_status_change_date():
    start = NOW.replace(hour=0)
    end = start + timedelta(days=1)
    last_week = start - timedelta(days=7)
    issues = [
        # moved to Done today, workflow never set a resolution
        make_issue("KAN-1", created=last_week, category="done", status="Done",
                   status_changed=NOW, updated=NOW),
        # closed last week, only commented on today -> not "closed today"
        make_issue("KAN-2", created=last_week, category="done", status="Done",
                   status_changed=last_week, updated=NOW),
    ]
    report = compute_daily_report(issues, start, end, set())
    assert [i.key for i in report.closed] == ["KAN-1"]
