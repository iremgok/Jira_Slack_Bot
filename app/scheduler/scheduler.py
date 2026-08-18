from __future__ import annotations
from apscheduler.schedulers.background import BackgroundScheduler

from app.config.settings import settings
from app.utils.logger import logger


class SchedulerServices:
    """
    Responsible for scheduling background jobs.
    """

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        """
        Configure and start scheduler.
        """
        logger.info("Starting Background Scheduler...")
        self._register_jobs()
        self.scheduler.start()

    def shutdown(self) -> None:
        """
        Stop scheduler.
        """
        logger.info("Stopping Background Scheduler...")
        self.scheduler.shutdown()

    def _sync_issues_job(self) -> None:
        """
        Run issue synchronization job.
        Manages its own database session and client lifetimes.
        """
        logger.info("Scheduled job: Starting Jira sync...")
        from app.database.db import SessionLocal
        from app.api.jira_client import JiraClient
        from app.api.slack_client import SlackClient
        from app.repositories.issue_repository import IssueRepository
        from app.repositories.notification_repository import NotificationRepository
        from app.services.notification_service import NotificationService
        from app.services.issue_service import IssueService
        
        session = SessionLocal()
        jira_client = JiraClient()
        slack_client = SlackClient()
        try:
            repository = IssueRepository(session)
            notification_repository = NotificationRepository(session)
            
            notification_service = NotificationService(
                slack_client=slack_client,
                repository=notification_repository
            )
            issue_service = IssueService(
                jira_client=jira_client,
                repository=repository,
                notification_service=notification_service
            )
            issue_service.sync_issues()
        except Exception as e:
            logger.exception(f"Exception occurred in scheduled sync_issues job: {e}")
        finally:
            jira_client.close()
            session.close()

    def _send_daily_report_job(self) -> None:
        """
        Run daily report job.
        Manages its own database session and client lifetimes.
        """
        logger.info("Scheduled job: Starting daily report...")
        from app.database.db import SessionLocal
        from app.api.slack_client import SlackClient
        from app.repositories.issue_repository import IssueRepository
        from app.repositories.notification_repository import NotificationRepository
        from app.repositories.report_repository import ReportRepository
        from app.services.notification_service import NotificationService
        from app.services.report_service import ReportService
        
        session = SessionLocal()
        slack_client = SlackClient()
        try:
            repository = IssueRepository(session)
            notification_repository = NotificationRepository(session)
            report_repository = ReportRepository(session)
            
            notification_service = NotificationService(
                slack_client=slack_client,
                repository=notification_repository
            )
            report_service = ReportService(
                repository=repository,
                notification_service=notification_service,
                report_repository=report_repository
            )
            report_service.send_daily_report()
        except Exception as e:
            logger.exception(f"Exception occurred in scheduled send_daily_report job: {e}")
        finally:
            session.close()

    def _register_jobs(self) -> None:
        """
        Register scheduled jobs.
        """
        logger.info("Registering scheduled jobs...")

        self.scheduler.add_job(
            func=self._sync_issues_job,
            trigger="interval",
            seconds=settings.check_interval,
            id="jira_sync",
            replace_existing=True,
        )

        self.scheduler.add_job(
            func=self._send_daily_report_job,
            trigger="cron",
            hour=18,
            minute=0,
            id="daily_report",
            replace_existing=True,
        )

        logger.info("Jobs registered successfully.")
