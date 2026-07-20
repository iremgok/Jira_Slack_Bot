from __future__ import annotations

from app.repositories.issue_repository import IssueRepository
from app.services.notification_service import NotificationService
from app.utils.logger import logger


class ReportService:
    """
    Service responsible for generating Jira reports.
    """

    def __init__(
        self,
        repository: IssueRepository,
        notification_service: NotificationService,
    ) -> None:

        self.repository = repository
        self.notification_service = notification_service


    def send_daily_report(self) -> bool:
        """
        Generate and send the daily Jira report.
        """

        logger.info("Generating daily Jira report.")

        created_today = self.repository.count_created_today()
        completed_today = self.repository.count_completed_today()
        blocked_issues = self.repository.count_blocked()
        top_assignee = self.repository.count_top_assignee()

        report = self._build_daily_report(
            created_today,
            completed_today,
            blocked_issues,
            top_assignee,
        )

        logger.info("Daily report generated succesfully.")

        return self.notification_service.send_message(report)


    @staticmethod
    def _build_daily_report(
            created_today: int,
            completed_today: int,
            blocked_issues: int,
            top_assignee: str,
    ) -> str:
        """
                Build the daily report message.
                """

        return (
            "📊 *Daily Jira Report*\n\n"
            f"🆕 Created Today: {created_today}\n"
            f"✅ Completed Today: {completed_today}\n"
            f"🚫 Blocked Issues: {blocked_issues}\n"
            f"👤 Top Assignee: {top_assignee}"
        )

