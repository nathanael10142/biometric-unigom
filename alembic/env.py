"""
Alembic env.py — targets the PRESENCE DB (rhunigom_presence) ONLY.

The production DB (rhunigom__database_production) is NEVER migrated here.
Its schema is managed by the HR system (Node.js/Sequelize).
We only ADD the biometric_id column to it manually via SQL.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.database import LocalBase

# Register all LOCAL models with LocalBase.metadata
import app.models.agent_cache    # noqa: F401
import app.models.attendance     # noqa: F401
import app.models.scan_log       # noqa: F401
import app.models.sync_cursor    # noqa: F401
import app.models.login_attempt  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Always use the presence DB URL for migrations
config.set_main_option("sqlalchemy.url", settings.DATABASE_PRESENCE_URL)

target_metadata = LocalBase.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
