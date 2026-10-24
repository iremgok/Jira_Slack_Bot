"""
Slack Block Kit message builders (presentation layer).

Pure functions: they take domain models and return a ``SlackMessage``.
Every issue title is rendered as a clickable link to ``/browse/<KEY>``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models.issue import FieldChange, JiraIssue
from src.models.report import DailyReport

MAX_LIST_ITEMS = 10
LIST_SUMMARY_LIMIT = 80   # 10 items x ~200 chars stays under the section limit
HEADER_LIMIT = 150        # Slack: header text max 150 chars
SECTION_LIMIT = 3000      # Slack: section text max 3000 chars (else "invalid_blocks")

PRIORITY_EMOJI = {
    "highest": "🔴", "critical": "🔴", "blocker": "🔴",
    "high": "🟠", "medium": "🟡", "low": "🟢", "lowest": "⚪",
}


@dataclass(frozen=True)
class SlackMessage:
    text: str  # notification / fallback text
    blocks: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------- #
# Small helpers
# ---------------------------------------------------------------------- #
def escape(text: str) -> str:
    """Escape the characters Slack mrkdwn treats as control characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def issue_link(issue: JiraIssue, summary_limit: int | None = None) -> str:
    summary = truncate(issue.summary, summary_limit) if summary_limit else issue.summary
    return f"<{issue.url}|{escape(f'{issue.key} — {summary}')}>"


def priority_badge(priority: str) -> str:
    return f"{PRIORITY_EMOJI.get(priority.lower(), '⚪')} {escape(priority)}"


def _header(text: str) -> dict[str, Any]:
    return {"type": "header", "text": {"type": "plain_text", "text": text[:HEADER_LIMIT], "emoji": True}}


def _section(markdown: str) -> dict[str, Any]:
    # Hard cap as a last resort; callers already keep content short
    return {"type": "section", "text": {"type": "mrkdwn", "text": truncate(markdown, SECTION_LIMIT)}}


def _fields(*pairs: tuple[str, str]) -> dict[str, Any]:
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f"*{label}*\n{value}"} for label, value in pairs],
    }


def _context(markdown: str) -> dict[str, Any]:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": markdown}]}


def _divider() -> dict[str, Any]:
    return {"type": "divider"}


def _issue_fields(issue: JiraIssue) -> dict[str, Any]:
    return _fields(
        ("Status", f"`{escape(issue.status)}`"),
        ("Priority", priority_badge(issue.priority)),
        ("Assignee", escape(issue.assignee_display)),
        ("Type", escape(issue.issue_type or "-")),
    )


def _issue_list(issues: list[JiraIssue], empty_text: str) -> str:
    if not issues:
        return f"_{empty_text}_"
    lines = [
        f"• {issue_link(i, LIST_SUMMARY_LIMIT)}  ·  {priority_badge(i.priority)}  ·  {escape(i.assignee_display)}"
        for i in issues[:MAX_LIST_ITEMS]
    ]
    if len(issues) > MAX_LIST_ITEMS:
        lines.append(f"_…and {len(issues) - MAX_LIST_ITEMS} more_")
    return "\n".join(lines)


# ---------------------------------------------------------------------- #
# Message builders
# ---------------------------------------------------------------------- #
def new_issue_message(issue: JiraIssue) -> SlackMessage:
    return SlackMessage(
        text=f"🆕 New issue {issue.key}: {issue.summary}",
        blocks=[
            _header("🆕 New Jira Issue"),
            _section(f"*{issue_link(issue)}*"),
            _issue_fields(issue),
            _context(f"Created {issue.created:%Y-%m-%d %H:%M} UTC"),
        ],
    )


def updated_issue_message(issue: JiraIssue, changes: list[FieldChange]) -> SlackMessage:
    change_lines = "\n".join(
        f"• *{c.field}:* `{escape(c.old)}` → `{escape(c.new)}`" for c in changes
    )
    return SlackMessage(
        text=f"✏️ {issue.key} updated: " + ", ".join(c.field for c in changes),
        blocks=[
            _header("✏️ Jira Issue Updated"),
            _section(f"*{issue_link(issue)}*"),
            _section(change_lines),
            _context(
                f"{priority_badge(issue.priority)}  ·  👤 {escape(issue.assignee_display)}"
                f"  ·  Updated {issue.updated:%Y-%m-%d %H:%M} UTC"
            ),
        ],
    )


def daily_report_message(report: DailyReport, project_key: str) -> SlackMessage:
    if report.top_assignees:
        assignee_lines = "\n".join(
            f"{idx}. {escape(a.name)} — *{a.open_issues}* open"
            for idx, a in enumerate(report.top_assignees, start=1)
        )
    else:
        assignee_lines = "_No open issues._"

    summary = (
        f"🆕 Opened: {len(report.created)} | ✅ Closed: {len(report.closed)} | "
        f"🔥 Open critical: {len(report.open_critical)}"
    )

    return SlackMessage(
        text=f"📊 Daily Jira report for {project_key} ({report.report_date:%Y-%m-%d}) — {summary}",
        blocks=[
            _header(f"📊 Daily Jira Report — {project_key} — {report.report_date:%d.%m.%Y}"),
            _fields(
                ("🆕 Opened today", f"*{len(report.created)}*"),
                ("✅ Closed today", f"*{len(report.closed)}*"),
                ("🔥 Open critical", f"*{len(report.open_critical)}*"),
                ("📂 Total open", f"*{report.total_open}*"),
            ),
            _divider(),
            _section("*🆕 Opened today*\n" + _issue_list(report.created, "No new issues today.")),
            _section("*✅ Closed today*\n" + _issue_list(report.closed, "Nothing closed today.")),
            _section(
                "*🔥 Open critical issues*\n"
                + _issue_list(report.open_critical, "No open critical issues. 🎉")
            ),
            _divider(),
            _section("*👥 Most loaded assignees (open issues)*\n" + assignee_lines),
        ],
    )
