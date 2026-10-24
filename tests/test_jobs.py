from datetime import timedelta

from src.database.repository import IssueRepository
from src.jobs.daily_report import DailyReportJob
from src.jobs.issue_poller import IssuePoller
from tests.conftest import NOW, FakeJira, FakeSlack, make_issue


def make_poller(database, jira, slack):
    return IssuePoller(jira=jira, slack=slack, database=database, project_key="KAN")


def test_poller_notifies_new_then_changes_then_nothing(database):
    jira, slack = FakeJira([make_issue("KAN-1")]), FakeSlack()
    poller = make_poller(database, jira, slack)

    assert poller.run().new == 1
    assert "-60m" in jira.queries[0]  # initial lookback window

    # Same version again -> no notification
    assert poller.run().new == 0
    assert len(slack.messages) == 1

    # Status changed -> update notification
    jira.issues = [make_issue("KAN-1", status="Done", category="done", updated=NOW + timedelta(hours=1))]
    assert poller.run().updated == 1
    assert "Status" in slack.messages[-1].text

    with database.session_scope() as session:
        assert IssueRepository(session).get_snapshots(["KAN-1"])["KAN-1"].status == "Done"


def test_poller_retries_failed_notifications(database):
    jira = FakeJira([make_issue("KAN-1"), make_issue("KAN-2")])
    slack = FakeSlack(fail_keys={"KAN-2"})
    poller = make_poller(database, jira, slack)

    result = poller.run()
    assert (result.new, result.failed) == (2, 1)

    slack.fail_keys.clear()
    result = poller.run()
    assert result.new == 1
    assert slack.messages[-1].text.startswith("🆕 New issue KAN-2")


def test_daily_report_sent_once_per_day(database):
    jira, slack = FakeJira([make_issue(priority="Highest")]), FakeSlack()
    job = DailyReportJob(jira=jira, slack=slack, database=database, project_key="KAN",
                         timezone_name="Europe/Istanbul", critical_priorities={"highest"})

    report = job.run(now=NOW)
    assert report is not None and len(report.open_critical) == 1
    assert job.run(now=NOW) is None                   # duplicate prevented
    assert job.run(now=NOW, force=True) is not None   # manual resend allowed
    assert len(slack.messages) == 2
    assert "statusCategory != Done" in jira.queries[0]


def test_poller_stops_on_slack_outage(database):
    jira = FakeJira([make_issue(f"KAN-{n}") for n in range(1, 6)])
    slack = FakeSlack(fail_keys={"KAN-"})  # every message fails
    result = make_poller(database, jira, slack).run()

    assert result.failed == 5
    assert slack.attempts == 1  # did not hammer Slack for every issue
    with database.session_scope() as session:
        assert IssueRepository(session).count() == 0  # nothing saved -> retried next poll
