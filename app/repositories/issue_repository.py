from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.issue import Issue
from app.utils.logger import logger


class IssueRepository:
    """
    Repository responsible for all issue database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def add(self, issue:Issue):
        """
        Add a new issue to the database
        """

        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        logger.info(f"issue '{issue.issue_key}' added.")
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

        self.db.commit()
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

        self.db.commit()
        logger.info(f"issue '{issue.issue_key}' mark as processed.")

        return True

    def get_unprocessed(self) -> list[Issue]:
        """
        Retrieve all unprocessed issues
        """

        statement = select(Issue).where(Issue.processed.is_(False))

        return list(self.db.scalars(statement).all())


