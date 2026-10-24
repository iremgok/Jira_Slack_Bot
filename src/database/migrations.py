"""
Programmatic access to Alembic, so the app can bring its schema up to date
on startup (``DB_AUTO_MIGRATE=true``) without a separate CLI step.
"""
from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"

# First migration; matches the schema the pre-Alembic ``create_all`` produced
BASELINE_REVISION = "42450821f736"
BASELINE_TABLES = {"tracked_issues", "job_state", "sent_reports"}


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    # ConfigParser treats '%' as interpolation (e.g. URL-encoded passwords)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["skip_logging"] = True  # keep the application's logging setup
    return config


def upgrade_database(database_url: str) -> None:
    """Apply all pending migrations (idempotent)."""
    config = build_alembic_config(database_url)

    if _is_unversioned_legacy_schema(database_url):
        logger.warning(
            "Existing tables found without Alembic version info; stamping baseline %s.",
            BASELINE_REVISION,
        )
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, "head")
    logger.info("Database migrations are up to date.")


def _is_unversioned_legacy_schema(database_url: str) -> bool:
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    return "alembic_version" not in tables and BASELINE_TABLES <= tables
