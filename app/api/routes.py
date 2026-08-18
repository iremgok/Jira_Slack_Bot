from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.jira_client import JiraClient
from app.api.slack_client import SlackClient
from app.database.db import SessionLocal
from app.repositories.issue_repository import IssueRepository
from app.services.issue_service import IssueService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService


router = APIRouter(
    prefix="",
    tags=["Jira Slack Bot"],
)


@router.get("/health")
def health_check():
    """
    Check whether the API is running.
    """

    return {
        "status": "healthy",
        "service": "jira-slack-bot",
    }


@router.get("/issues")
def get_issues():
    """
    Return all issues.
    """

    session = SessionLocal()

    try:
        repository = IssueRepository(session)

        issues = repository.get_all()

        return issues

    finally:
        session.close()


@router.get("/issues/{issue_key}")
def get_issue(issue_key: str):
    """
    Return a single issue.
    """

    session = SessionLocal()

    try:
        repository = IssueRepository(session)

        issue = repository.get_by_key(issue_key)

        if issue is None:
            raise HTTPException(
                status_code=404,
                detail="Issue not found.",
            )

        return issue

    finally:
        session.close()


@router.post("/sync")
def sync_issues():
    """
    Synchronize Jira issues.
    """

    session = SessionLocal()

    try:
        jira_client = JiraClient()
        slack_client = SlackClient()

        repository = IssueRepository(session)

        notification_service = NotificationService(
            slack_client
        )

        issue_service = IssueService(
            jira_client=jira_client,
            repository=repository,
            notification_service=notification_service,
        )

        issue_service.sync_issues()

        return {
            "message": "Synchronization completed.",
        }

    finally:
        session.close()


@router.post("/report")
def send_report():
    """
    Send the daily report.
    """

    session = SessionLocal()

    try:
        repository = IssueRepository(session)

        slack_client = SlackClient()

        notification_service = NotificationService(
            slack_client
        )

        report_service = ReportService(
            repository=repository,
            notification_service=notification_service,
        )

        report_service.send_daily_report()

        return {
            "message": "Report sent.",
        }

    finally:
        session.close()

