from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.enums.issue_status import IssueStatus
from app.enums.priority import IssuePriority


class Issue(Base):
    """
    Represent a jira issue stored a local database.
    """

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key = True,
        autoincrement = True
    )

    issue_key: Mapped[str] = mapped_column(
        String(50),
        unique = True,
        nullable = False,
        index = True
    )

    summary: Mapped[str] = mapped_column(
        String(500),
        nullable = False
    )

    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus),
        nullable = False
    )

    priority: Mapped[IssuePriority] = mapped_column(
        Enum(IssuePriority),
        nullable= False
    )

    assignee: Mapped[str | None] = mapped_column(
        String(255),
        nullable = True   #Her issue'nin atanmış kişisi olmayabilir.
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable = False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable = False
    )

    processed: Mapped[bool] = mapped_column(  # Bu alan bize ait duplicate önlenecek.
        Boolean,
        default = False,
        nullable = False
    )

    inserted_at: Mapped[datetime] = mapped_column(   # Veritabanımıza ne zaman kaydedildiğini gösterir.
        DateTime(timezone = True),
        default = lambda: datetime.now(UTC),
        nullable = False
    )

    def __repr__(self) -> str:
        return (
            f"Issue("
            f"issue_key='{self.issue_key}', "
            f"status='{self.status.value}', "
            f"priority='{self.priority.value}')"
        )



















