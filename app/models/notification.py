from datetime import UTC, datetime
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class NotificationLog(Base):
    """
    Database model to log notifications sent to Slack.
    """
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    issue_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    notification_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # e.g., "new", "updated", "error"
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
            f"NotificationLog("
            f"issue_key='{self.issue_key}', "
            f"type='{self.notification_type}', "
            f"success={self.success})"
        )
