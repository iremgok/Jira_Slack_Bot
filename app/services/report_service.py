from __future__ import annotations

from app.repositories.issue_repository import IssueRepository
from app.repositories.report_repository import ReportRepository
from app.services.notification_service import NotificationService
from app.utils.logger import logger
from app.utils.formatter import build_daily_report_message


class ReportService:
    """
    Service responsible for generating and sending Jira reports, logging results.
    """

    def __init__(
        self,
        repository: IssueRepository,
        notification_service: NotificationService,
        report_repository: ReportRepository | None = None,
    ) -> None:
        self.repository = repository
        self.notification_service = notification_service
        self.report_repository = report_repository

    def send_daily_report(self) -> bool:
        """
        Generate and send the daily Jira report, then log it.
        """
        logger.info("Generating daily Jira report...")

        created_today = self.repository.count_created_today()
        completed_today = self.repository.count_completed_today()
        open_critical = self.repository.count_open_critical()
        top_assignee = self.repository.get_top_assignee()

        report_text, blocks = build_daily_report_message(
            created_today=created_today,
            completed_today=completed_today,
            open_critical=open_critical,
            top_assignee=top_assignee,
        )

        success = False
        error_message = None

        logger.info("Daily report generated successfully.")
        try:
            success = self.notification_service.send_message(report_text, blocks)
        except Exception as exc:
            error_message = str(exc)
            logger.error(f"Error sending daily report: {exc}")
            raise exc
        finally:
            if self.report_repository:
                try:
                    self.report_repository.create_log(
                        report_type="daily",
                        created_count=created_today,
                        completed_count=completed_today,
                        open_critical_count=open_critical,
                        top_assignee=top_assignee,
                        success=success,
                        error_message=error_message,
                    )
                except Exception as log_exc:
                    logger.error(f"Failed to record report log to database: {log_exc}")

        return success
