from datetime import UTC, datetime
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReportLog(Base):
    """
    Database model to log reports sent to Slack.
    """
    __tablename__ = "report_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    report_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # e.g., "daily"
    created_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    completed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    open_critical_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    top_assignee: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"ReportLog("
            f"type='{self.report_type}', "
            f"success={self.success})"
        )
