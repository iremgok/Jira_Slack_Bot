"""
Alembic environment.

* Target metadata comes from ``src.database.tables`` (single source of truth).
* The URL comes from ``DATABASE_URL`` unless the caller already set
  ``sqlalchemy.url`` (as ``src.database.migrations`` does).
* ``render_as_batch`` lets ALTER TABLE style migrations work on SQLite.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.core.config import DatabaseSettings
from src.database import tables  # noqa: F401 - registers tables on Base.metadata
from src.database.db import Base

config = context.config

# When run from the application, keep the app's own logging configuration
if config.config_file_name is not None and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name)

if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", DatabaseSettings().database_url)

target_metadata = Base.metadata


def _configure_kwargs(url: str) -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "render_as_batch": url.startswith("sqlite"),
    }


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it (``alembic upgrade head --sql``)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True, **_configure_kwargs(url))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, **_configure_kwargs(url))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
