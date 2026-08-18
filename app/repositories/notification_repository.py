from sqlalchemy.orm import Session

from app.exceptions.custom_exceptions import RepositoryError
from app.models.notification import NotificationLog
from app.utils.logger import logger


class NotificationRepository:
    """
    Repository responsible for storing and retrieving notification logs.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        issue_key: str,
        notification_type: str,
        success: bool,
        error_message: str | None = None,
    ) -> NotificationLog:
        """
        Record a notification delivery status to the database.
        """
        log = NotificationLog(
            issue_key=issue_key,
            notification_type=notification_type,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        try:
            self.db.commit()
            self.db.refresh(log)
            logger.info(
                f"Notification log recorded for '{issue_key}' "
                f"(type={notification_type}, success={success})."
            )
        except Exception as error:
            self.db.rollback()
            raise RepositoryError(
                "Database transaction failed during notification logging."
            ) from error
        return log
