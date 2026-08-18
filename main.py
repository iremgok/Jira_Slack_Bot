from app.api.jira_client import JiraClient
from app.api.slack_client import SlackClient
from app.database.base import Base
from app.database.db import sessionLocal, engine
from app.repositories.issue_repository import IssueRepository
from app.services.issue_service import IssueService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.scheduler.scheduler import SchedulerServices
from app.utils.logger import logger
from fastapi import FastAPI
from app.api.routes import router



def main() -> None:
    """
    Application entry point.
    """

    app = FastAPI(
        title="Jira Slack Bot",
        version="1.0.0",
    )

    app.include_router(router)

    logger.info("Starting Jira Slack Bot...")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Database session
    session = sessionLocal()

    # Clients
    jira_client = JiraClient()
    slack_client = SlackClient()

    # Repository
    repository = IssueRepository(session)

    # Services
    notification_service = NotificationService(slack_client)

    issue_service = IssueService(
        jira_client=jira_client,
        repository=repository,
        notification_service=notification_service,
    )

    report_service = ReportService(
        repository=repository,
        notification_service=notification_service,
    )

    # Scheduler
    scheduler = SchedulerServices(
        issue_services = issue_service,
        report_services = report_service,
    )

    try:
        logger.info("Application started successfully.")

        scheduler.start()

    except KeyboardInterrupt:
        logger.info("Application stopped by user.")

    finally:
        jira_client.close()
        session.close()


if __name__ == "__main__":
    main()
