"""
Application entry point (composition root).

    python -m src.main                 # start the scheduler (default)
    python -m src.main --once poll     # run the issue poller once and exit
    python -m src.main --once report   # send today's report now (even if already sent)
    python -m src.main --check         # verify Jira / Slack connectivity
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import ValidationError

from src.core.config import Settings, get_settings
from src.core.exceptions import BotError
from src.core.logger import setup_logging
from src.database.db import Database, safe_url, wait_for_database
from src.database.migrations import upgrade_database
from src.jobs.daily_report import DailyReportJob
from src.jobs.issue_poller import IssuePoller
from src.services.jira_client import IssueSource, JiraClient
from src.services.jira_mock import MockJiraClient
from src.services.slack_client import SlackClient

logger = logging.getLogger("src.main")

REPORT_RETRY_ATTEMPTS = 3
REPORT_RETRY_DELAY = timedelta(minutes=10)


@dataclass
class App:
    settings: Settings
    database: Database
    jira: IssueSource
    slack: SlackClient
    poller: IssuePoller
    daily_report: DailyReportJob

    def close(self) -> None:
        self.jira.close()
        self.slack.close()
        self.database.dispose()


def build_app(settings: Settings) -> App:
    """Wire all dependencies together. The only place that knows concrete classes."""
    log_startup_summary(settings)
    wait_for_database(settings.database_url, settings.db_connect_timeout_seconds)
    if settings.db_auto_migrate:
        upgrade_database(settings.database_url)
    database = Database(settings.database_url)

    jira: IssueSource
    if settings.jira_mock_mode:
        logger.warning("JIRA_MOCK_MODE is enabled - using sample data instead of Jira.")
        jira = MockJiraClient(settings.jira_base_url, settings.jira_project_key)
    else:
        jira = JiraClient(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token.get_secret_value(),
            timeout=settings.jira_timeout_seconds,
        )

    slack = SlackClient(
        webhook_url=settings.slack_webhook_url.get_secret_value(),
        bot_token=settings.slack_bot_token.get_secret_value(),
        channel=settings.slack_channel,
        dry_run=settings.slack_dry_run,
    )

    poller = IssuePoller(
        jira=jira,
        slack=slack,
        database=database,
        project_key=settings.jira_project_key,
        extra_jql=settings.jira_extra_jql,
        initial_lookback_minutes=settings.initial_lookback_minutes,
    )
    daily_report = DailyReportJob(
        jira=jira,
        slack=slack,
        database=database,
        project_key=settings.jira_project_key,
        timezone_name=settings.timezone,
        critical_priorities=settings.critical_priority_set,
        top_assignee_count=settings.top_assignee_count,
        extra_jql=settings.jira_extra_jql,
    )
    return App(settings, database, jira, slack, poller, daily_report)


def log_startup_summary(settings: Settings) -> None:
    """Log the effective (non-secret) configuration - invaluable during live tests."""
    if settings.slack_dry_run:
        slack_mode = "dry-run (messages are only logged)"
    elif settings.slack_webhook_url.get_secret_value():
        slack_mode = "incoming webhook"
    else:
        slack_mode = f"bot token -> channel {settings.slack_channel}"
    jira_target = "MOCK sample data" if settings.jira_mock_mode else settings.jira_base_url

    logger.info(
        "Config: jira=%s project=%s extra_jql=%r | slack=%s | db=%s (auto-migrate=%s) | tz=%s",
        jira_target, settings.jira_project_key, settings.jira_extra_jql or "", slack_mode,
        safe_url(settings.database_url), settings.db_auto_migrate, settings.timezone,
    )


def _safe(job_name: str, func: Callable[[], object]) -> Callable[[], None]:
    """Wrap a job so one failure never kills the scheduler."""
    def runner() -> None:
        try:
            func()
        except BotError as exc:  # expected integration failure: clear message, no traceback
            logger.error("Job '%s' failed: %s", job_name, exc)
        except Exception:  # noqa: BLE001 - last line of defence for scheduled jobs
            logger.exception("Job '%s' crashed unexpectedly.", job_name)
    return runner


def run_scheduler(app: App) -> None:
    settings = app.settings
    scheduler = BlockingScheduler(timezone=settings.timezone)

    scheduler.add_job(
        _safe("issue_poller", app.poller.run),
        trigger="interval",
        seconds=settings.poll_interval_seconds,
        id="issue_poller",
        next_run_time=datetime.now(scheduler.timezone),  # run once immediately
        max_instances=1,
        coalesce=True,
    )
    def daily_report_with_retry(attempt: int = 1) -> None:
        try:
            app.daily_report.run()
        except BotError as exc:
            if attempt >= REPORT_RETRY_ATTEMPTS:
                logger.error("Daily report failed after %d attempt(s): %s", attempt, exc)
                return
            retry_at = datetime.now(scheduler.timezone) + REPORT_RETRY_DELAY
            logger.error("Daily report failed (attempt %d): %s. Retrying at %s.",
                         attempt, exc, retry_at.strftime("%H:%M"))
            scheduler.add_job(_safe("daily_report_retry", lambda: daily_report_with_retry(attempt + 1)),
                              trigger="date", run_date=retry_at, id="daily_report_retry",
                              replace_existing=True)

    scheduler.add_job(
        _safe("daily_report", daily_report_with_retry),
        trigger=CronTrigger.from_crontab(settings.daily_report_cron, timezone=settings.timezone),
        id="daily_report",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,  # still send if the bot was briefly down at 18:00
    )

    def _shutdown(signum, _frame) -> None:
        logger.info("Received signal %s, shutting down...", signum)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        "Scheduler started: poll every %ss, daily report cron '%s' (%s).",
        settings.poll_interval_seconds, settings.daily_report_cron, settings.timezone,
    )
    scheduler.start()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jira issue tracker & Slack report bot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", choices=("poll", "report"), help="run a single job and exit")
    group.add_argument("--check", action="store_true", help="check Jira and Slack connectivity")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        settings = get_settings()
    except ValidationError as exc:
        setup_logging("INFO", log_dir=None)
        # Log only messages, never the input values (they may contain secrets)
        problems = "\n".join(
            f"  - {'.'.join(map(str, err['loc'])) or 'settings'}: {err['msg']}"
            for err in exc.errors(include_input=False)
        )
        logger.error("Invalid configuration:\n%s", problems)
        return 2

    setup_logging(settings.log_level, settings.log_dir)
    app: App | None = None
    try:
        app = build_app(settings)
        if args.check:
            jira_ok, slack_ok = app.jira.health_check(), app.slack.health_check()
            logger.info("Jira: %s | Slack: %s", "OK" if jira_ok else "FAIL", "OK" if slack_ok else "FAIL")
            return 0 if jira_ok and slack_ok else 1
        if args.once == "poll":
            result = app.poller.run()
            return 1 if result.failed else 0
        if args.once == "report":
            app.daily_report.run(force=True)
            return 0
        run_scheduler(app)
        return 0
    except BotError as exc:
        logger.error("%s: %s", type(exc).__name__, exc)
        logger.debug("Traceback:", exc_info=True)
        return 1
    except Exception:  # noqa: BLE001
        logger.exception("Fatal error.")
        return 1
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    sys.exit(main())
