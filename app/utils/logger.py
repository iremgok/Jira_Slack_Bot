import logging
from pathlib import Path
from app.config.settings import settings

class AppLogger:
    """
    Creates and configures the application's central logger.

    This class ensures that every module in the application
    uses the same logger instance and formatting.
    """

    _logger = None

    @classmethod
    def get_logger(cls) -> logging.Logger:

        if cls._logger:
            return cls._logger

        log_directory = Path("logs")
        log_directory.mkdir(exist_ok=True)

        logger = logging.getLogger(settings.app_name)
        logger.setLevel(settings.log_level)

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)8s | %(levelname)s | %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(
            log_directory / "app.log",
            encoding = "utf-8"
        )

        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        cls._logger = logger
        return logger

logger = AppLogger.get_logger()
