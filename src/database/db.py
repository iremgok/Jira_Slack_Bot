"""
Database connection management (SQLite or PostgreSQL via SQLAlchemy 2.x).
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.exceptions import RepositoryError

logger = logging.getLogger(__name__)


# Deterministic constraint names keep Alembic migrations stable across databases
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM tables."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Database:
    """Owns the engine and hands out transactional sessions."""

    def __init__(self, url: str, echo: bool = False) -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            url, echo=echo, pool_pre_ping=True, connect_args=connect_args
        )
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", _enable_sqlite_wal)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        """
        Create tables straight from the ORM metadata (tests / throwaway DBs).
        Real databases are managed by Alembic - see ``src.database.migrations``.
        """
        # Import registers the table classes on Base.metadata
        from src.database import tables  # noqa: F401

        Base.metadata.create_all(self.engine)
        logger.info("Database schema is ready (%s).", self.engine.url.render_as_string(hide_password=True))

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Commit on success, roll back on error, always close."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise RepositoryError(f"Database transaction failed: {exc}") from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()


def _enable_sqlite_wal(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def safe_url(url: str) -> str:
    """Database URL with the password masked, safe for logs."""
    return make_url(url).render_as_string(hide_password=True)


def wait_for_database(url: str, timeout_seconds: int = 60, interval_seconds: float = 2.0) -> None:
    """
    Block until the database accepts connections (e.g. PostgreSQL still starting
    in Docker). Raises ``RepositoryError`` once ``timeout_seconds`` is exceeded.
    """
    engine = create_engine(url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    try:
        while True:
            attempt += 1
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                if attempt > 1:
                    logger.info("Database is reachable after %d attempt(s).", attempt)
                return
            except OperationalError as exc:
                if time.monotonic() >= deadline:
                    raise RepositoryError(
                        f"Database {safe_url(url)} not reachable after {timeout_seconds}s: "
                        f"{getattr(exc, 'orig', exc)}"
                    ) from None
                logger.warning("Waiting for database %s (attempt %d)...", safe_url(url), attempt)
                time.sleep(interval_seconds)
    finally:
        engine.dispose()
