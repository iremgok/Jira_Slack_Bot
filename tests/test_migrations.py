from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from src.database import tables  # noqa: F401
from src.database.db import Base, Database
from src.database.migrations import BASELINE_REVISION, build_alembic_config, upgrade_database


def _url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


def _current_revision(url: str) -> str | None:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def test_migrations_match_orm_tables(tmp_path):
    """Fails if tables.py changed without a matching Alembic revision."""
    url = _url(tmp_path)
    upgrade_database(url)

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    assert diff == [], f"Run 'alembic revision --autogenerate'. Pending changes: {diff}"


def test_upgrade_is_idempotent(tmp_path):
    url = _url(tmp_path)
    upgrade_database(url)
    upgrade_database(url)
    assert _current_revision(url) is not None


def test_legacy_create_all_database_is_stamped(tmp_path):
    url = _url(tmp_path)
    legacy = Database(url)
    legacy.create_tables()  # schema created before Alembic existed
    legacy.dispose()

    upgrade_database(url)
    assert _current_revision(url) is not None


def test_downgrade_to_base_removes_tables(tmp_path):
    url = _url(tmp_path)
    upgrade_database(url)
    command.downgrade(build_alembic_config(url), "base")

    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()


def test_baseline_revision_exists():
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(build_alembic_config("sqlite://"))
    assert script.get_revision(BASELINE_REVISION) is not None
