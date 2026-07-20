from __future__ import annotations
from apscheduler.schedulers.blocking import BlockingScheduler

from app.config.settings import settings
from app.services.issue_service import IssueService
from app.services.report_service import ReportService
from app.utils.logger import logger


class SchedulerServices:
    """
    Responsible for scheduling background jobs.
    """

    def __init__(
            self,
            issue_services: IssueService,
            report_services: ReportService,
    ) -> None:

        self.scheduler = BlockingScheduler()
        self.issue_services = issue_services
        self.report_services = report_services


    def start(self) -> None:
        """
        Configure and start scheduler.
        """

        logger.info("Starting Scheduler...")

        self._register_jobs()
        self.scheduler.start()


    def _register_jobs(self) -> None:
        """
        Register scheduled jobs.
        """

        logger.info("Registering scheduled jobs")

        self.scheduler.add_job(
            func = self.issue_service.sync_issues,
            trigger = "interval",
            seconds = settings.check_interval,
            id = "jira_sync",
            replace_existing = True,
        )

        self.scheduler.add_job(
            func = self.report_service.send_daily_report,
            trigger = "cron",
            hour = 18,
            minute = 0,
            id = "daily_report",
            replace_existing = True,
        )

        logger.info("Jobs registered successfully.")

