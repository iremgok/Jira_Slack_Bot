from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.enums.issue_status import IssueStatus
from app.exceptions.custom_exceptions import RepositoryError
from app.models.issue import Issue
from app.utils.logger import logger



class IssueRepository:
    """
    Repository responsible for all issue database operations.
    """

    def __init__(self, db: Session):
        self.db = db


    def create(self, issue:Issue) -> Issue:
        """
        Create a new issue to the database
        """

        self.db.add(issue)
        try:

            self.db.commit()

        except Exception as error:

            self.db.rollback()

            raise RepositoryError(
                "Database transaction failed."
            ) from error
        self.db.refresh(issue)

        logger.info(f"issue '{issue.issue_key}' created.")

        return issue


    def get_by_key(self, issue_key: str) -> Issue | None:
        """
        Retrieve an issue by its jira key
        """

        statement = select(Issue).where(Issue.issue_key == issue_key)

        return self.db.scalar(statement)


    def exists(self, issue_key: str) -> bool:
        """"
        Check whether an issue already exits.
        """

        return self.get_by_key(issue_key) is not None


    def update(self, issue: Issue) -> Issue:
        """
        Update an existing issue
        """

        try:

            self.db.commit()
            self.db.refresh(issue)

        except Exception as error:

            self.db.rollback()

            raise RepositoryError(
                "Database transaction failed."
            ) from error
        self.db.refresh(issue)

        logger.info(f"issue '{issue.issue_key}' updated.")

        return issue


    def mark_as_processed(self, issue_key: str) -> bool:
        """
        Mark an issue as processed
        """

        issue = self.get_by_key(issue_key)

        if issue is None:
            return False

        issue.processed = True

        try:

            self.db.commit()

        except Exception as error:

            self.db.rollback()

            raise RepositoryError(
                "Database transaction failed."
            ) from error

        logger.info(f"issue '{issue.issue_key}' marked as processed.")

        return True


    def get_unprocessed(self) -> list[Issue]:
        """
        Retrieve all unprocessed issues
        """

        statement = select(Issue).where(Issue.processed.is_(False))

        return list(self.db.scalars(statement).all())


    def get_all(self) -> list[Issue]:
        """
        Retrieve all issues ordered by last update.
        """

        statement = (
            select(Issue)
            .order_by(desc(Issue.updated_at))
        )

        return list(self.db.scalars(statement).all())


    def count_created_today(self) -> int:
        """
        Count issues created today.
        """

        today = datetime.now(UTC).date()

        statement = (
            select(func.count())
            .select_from(Issue)
            .where(func.date(Issue.created_at) == today)
        )

        return self.db.scalar(statement) or 0


    def count_completed_today(self) -> int:
        """
        Count completed issues today.
        """

        today = datetime.now(UTC).date()

        statement = (
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.status == IssueStatus.DONE,
                func.date(Issue.updated_at) == today,
            )
        )

        return self.db.scalar(statement) or 0


    def count_blocked(self) -> int:
        """
        Count blocked issues.
        """

        statement = (
            select(func.count())
            .select_from(Issue)
            .where(Issue.status == IssueStatus.BLOCKED)
        )

        return self.db.scalar(statement) or 0


    def get_top_assignee(self) -> str:
        """
        Return the assignee with the highest number of issues.
        """

        statement = (
            select(
                Issue.assignee,
                func.count(Issue.id).label("total")
            )
            .where(Issue.assignee.is_not(None))
            .group_by(Issue.assignee)
            .order_by(desc("total"))
        )

        result = self.db.execute(statement).first()

        if result is None:
            return "No assignee"

        return f"{result.assignee} ({result.total})"


    def _commit(self) -> None:
        """
        Commit current transaction.
        """

        try:
            self.db.commit()

        except Exception as error:

            self.db.rollback()

            raise RepositoryError(
                "Database transaction failed."
            ) from error
