from typing import Any

from app.config.settings import settings
from app.models.issue import Issue


def build_new_issue_message(issue: Issue) -> tuple[str, list[dict[str, Any]]]:
    """
    Build plain text fallback and Block Kit payload for a new issue notification.
    """
    jira_url = settings.jira_url.rstrip("/")
    issue_url = f"{jira_url}/browse/{issue.issue_key}"

    text_message = (
        f"🔔 *New Jira Issue Created*\n\n"
        f"*Key:* {issue.issue_key} ({issue_url})\n"
        f"*Summary:* {issue.summary}\n"
        f"*Status:* {issue.status.value}\n"
        f"*Priority:* {issue.priority.value}\n"
        f"*Assignee:* {issue.assignee or 'Unassigned'}"
    )

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔔 New Jira Issue Created",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key:* <{issue_url}|{issue.issue_key}>\n*Summary:* {issue.summary}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n`{issue.status.value}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Priority:*\n`{issue.priority.value}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Assignee:*\n`{issue.assignee or 'Unassigned'}`"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]
    return text_message, blocks


def build_updated_issue_message(issue: Issue, changes: list[str]) -> tuple[str, list[dict[str, Any]]]:
    """
    Build plain text fallback and Block Kit payload for an updated issue notification.
    """
    jira_url = settings.jira_url.rstrip("/")
    issue_url = f"{jira_url}/browse/{issue.issue_key}"
    changes_str = "\n".join(changes)

    text_message = (
        f"✏️ *Jira Issue Updated*\n\n"
        f"*Key:* {issue.issue_key} ({issue_url})\n"
        f"*Changes:*\n{changes_str}"
    )

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✏️ Jira Issue Updated",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key:* <{issue_url}|{issue.issue_key}> - {issue.summary}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tracked Changes:*\n{changes_str}"
            }
        },
        {
            "type": "divider"
        }
    ]
    return text_message, blocks


def build_daily_report_message(
    created_today: int,
    completed_today: int,
    open_critical: int,
    top_assignee: str
) -> tuple[str, list[dict[str, Any]]]:
    """
    Build plain text fallback and Block Kit payload for the daily report.
    """
    report_text = (
        f"📊 *Daily Jira Summary Report*\n\n"
        f"🆕 *Created Today:* {created_today}\n"
        f"✅ *Completed Today:* {completed_today}\n"
        f"⚠️ *Open Critical Issues:* {open_critical}\n"
        f"👤 *Top Assignee:* {top_assignee}"
    )

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Daily Jira Summary Report",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"🆕 *Created Today:*\n`{created_today}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"✅ *Completed Today:*\n`{completed_today}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Open Critical Issues:*\n`{open_critical}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"👤 *Top Assignee:*\n`{top_assignee}`"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]
    return report_text, blocks


def build_error_message(error_message: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Build plain text fallback and Block Kit payload for an error notification.
    """
    text_message = f"🚨 *Jira Bot Error*\n\n{error_message}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Jira Bot Error",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"An unexpected error occurred in the bot service:\n```{error_message}```"
            }
        }
    ]
    return text_message, blocks
