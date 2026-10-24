"""ORM table definitions used for tracking state between runs."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrackedIssue(Base):
    """Last known snapshot of an issue, used to detect new/changed issues."""

    __tablename__ = "tracked_issues"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    status_category: Mapped[str] = mapped_column(String(50), default="")
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class JobState(Base):
    """Simple key/value store for job cursors (e.g. last successful poll)."""

    __tablename__ = "job_state"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)


class SentReport(Base):
    """One row per delivered daily report; prevents duplicate sends."""

    __tablename__ = "sent_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    open_critical_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
