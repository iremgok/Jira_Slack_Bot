"""
Database connection management (SQLite or PostgreSQL via SQLAlchemy 2.x).
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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
