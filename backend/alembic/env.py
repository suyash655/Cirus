"""CIRUS — Alembic environment configuration.

WHY ASYNC ENV:
CIRUS uses SQLAlchemy 2.0 async engine (create_async_engine + AsyncSession).
Alembic's default env.py uses the synchronous engine API, which is
incompatible. We use run_sync() to run Alembic's synchronous migration
operations through the async engine.

OFFLINE MODE (generates SQL script, no DB connection needed):
    alembic upgrade head --sql > migration.sql

ONLINE MODE (applies migrations to live DB):
    alembic upgrade head

ENVIRONMENT DETECTION:
    Reads DATABASE_URL from the app's Pydantic settings — the same value
    FastAPI uses. No duplicate config. Supports both SQLite (dev) and
    PostgreSQL (staging/prod) via the same env.py.
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Path setup — make app importable ─────────────────────────────────────────
# env.py lives at backend/alembic/env.py; backend/ must be on the path.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Import all models so their tables are registered on Base.metadata.
# Alembic's autogenerate compares this metadata against the live DB schema.
import app.models  # noqa: F401, E402  (side-effect: registers all ORM models)

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Set the database URL from app settings (overrides alembic.ini [database] url).
# This ensures we always use the same DATABASE_URL as the running app.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging. This line sets up loggers
# specified in alembic.ini (avoids duplicate setup with app's structlog).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate (compares ORM models vs. live schema).
target_metadata = Base.metadata


# ── Offline migration (--sql mode) ────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL migration script without a live DB connection.

    Useful for reviewing what will run before applying, or for DBAs who
    apply migrations manually in production.

        alembic upgrade head --sql > migration_YYYYMMDD.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas to detect cross-schema changes (PostgreSQL).
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online migration (applies to live DB) ─────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the async engine.

    Alembic's migration functions are synchronous, so we thread them through
    run_sync() which executes them in a synchronous context under the event loop.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: no persistent connections during migration
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (live DB) migrations."""
    asyncio.run(run_async_migrations())


# ── Dispatch ──────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
