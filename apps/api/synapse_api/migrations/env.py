"""Alembic migration environment supporting both PostgreSQL and SQLite."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context

from synapse_api.db import create_db_engine
from synapse_api.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _resolved_url() -> str:
    env_url = os.environ.get("SYNAPSE_DATABASE_URL")
    if env_url:
        return env_url
    cfg_url = config.get_main_option("sqlalchemy.url")
    if cfg_url is None:
        raise RuntimeError("Missing sqlalchemy.url in Alembic configuration")
    return cfg_url


def run_migrations_offline() -> None:
    context.configure(
        url=_resolved_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _resolved_url()
    connectable = create_db_engine(url)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
