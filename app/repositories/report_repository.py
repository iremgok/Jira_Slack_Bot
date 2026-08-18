from sqlalchemy.orm import Session

from app.exceptions.custom_exceptions import RepositoryError
from app.models.report import ReportLog
from app.utils.logger import logger


class ReportRepository:
    """
    Repository responsible for storing and retrieving report logs.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        report_type: str,
        created_count: int,
        completed_count: int,
        open_critical_count: int,
        top_assignee: str,
        success: bool,
        error_message: str | None = None,
    ) -> ReportLog:
        """
        Record a report delivery status to the database.
        """
        log = ReportLog(
            report_type=report_type,
            created_count=created_count,
            completed_count=completed_count,
            open_critical_count=open_critical_count,
            top_assignee=top_assignee,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        try:
            self.db.commit()
            self.db.refresh(log)
            logger.info(
                f"Report log recorded (type={report_type}, success={success})."
            )
        except Exception as error:
            self.db.rollback()
            raise RepositoryError(
                "Database transaction failed during report logging."
            ) from error
        return log
