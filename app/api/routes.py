from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.jira_client import JiraClient
from app.api.slack_client import SlackClient
from app.database.db import SessionLocal
from app.repositories.issue_repository import IssueRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.report_repository import ReportRepository
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
    Check whether the API is running and check external integration health.
    """
    jira_client = JiraClient()
    slack_client = SlackClient()
    try:
        jira_health = jira_client.health_check()
        slack_health = slack_client.health_check()
        
        status = "healthy" if jira_health and slack_health else "unhealthy"
        
        return {
            "status": status,
            "service": "jira-slack-bot",
            "integrations": {
                "jira": "connected" if jira_health else "disconnected",
                "slack": "connected" if slack_health else "disconnected"
            }
        }
    finally:
        jira_client.close()


@router.get("/issues")
def get_issues():
    """
    Return all issues stored in the local database.
    """
    session = SessionLocal()
    try:
        repository = IssueRepository(session)
        issues = repository.get_all()
        return [
            {
                "id": issue.id,
                "issue_key": issue.issue_key,
                "summary": issue.summary,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "assignee": issue.assignee,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                "processed": issue.processed,
                "inserted_at": issue.inserted_at.isoformat() if issue.inserted_at else None,
            }
            for issue in issues
        ]
    finally:
        session.close()


@router.get("/issues/{issue_key}")
def get_issue(issue_key: str):
    """
    Return a single issue by its key.
    """
    session = SessionLocal()
    try:
        repository = IssueRepository(session)
        issue = repository.get_by_key(issue_key)

        if issue is None:
            raise HTTPException(
                status_code=404,
                detail=f"Issue {issue_key} not found.",
            )

        return {
            "id": issue.id,
            "issue_key": issue.issue_key,
            "summary": issue.summary,
            "status": issue.status.value,
            "priority": issue.priority.value,
            "assignee": issue.assignee,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "processed": issue.processed,
            "inserted_at": issue.inserted_at.isoformat() if issue.inserted_at else None,
        }
    finally:
        session.close()


@router.post("/sync")
def sync_issues():
    """
    Synchronize Jira issues on demand.
    """
    session = SessionLocal()
    jira_client = JiraClient()
    slack_client = SlackClient()

    try:
        repository = IssueRepository(session)
        notification_repository = NotificationRepository(session)
        
        notification_service = NotificationService(
            slack_client=slack_client,
            repository=notification_repository,
        )
        
        issue_service = IssueService(
            jira_client=jira_client,
            repository=repository,
            notification_service=notification_service,
        )

        issue_service.sync_issues()

        return {
            "message": "Synchronization completed successfully.",
        }
    finally:
        jira_client.close()
        session.close()


@router.post("/report")
def send_report():
    """
    Send the daily summary report to Slack on demand.
    """
    session = SessionLocal()
    slack_client = SlackClient()

    try:
        repository = IssueRepository(session)
        notification_repository = NotificationRepository(session)
        report_repository = ReportRepository(session)
        
        notification_service = NotificationService(
            slack_client=slack_client,
            repository=notification_repository,
        )
        
        report_service = ReportService(
            repository=repository,
            notification_service=notification_service,
            report_repository=report_repository,
        )

        report_service.send_daily_report()

        return {
            "message": "Report sent successfully.",
        }
    finally:
        session.close()
