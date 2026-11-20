"""SQLAlchemy engine/session setup and programmatic Alembic migration helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL or local SQLite (WAL + FK pragmas)."""
    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        db_name = url.database or ""
        if db_name and db_name != ":memory:":
            Path(db_name).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn: Any, _conn_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if db_name and db_name != ":memory:":
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        return engine

    return create_engine(database_url, pool_pre_ping=True, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a typed session factory preserving attributes after commit."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def build_alembic_config(database_url: str) -> Config:
    """Build programmatic Alembic configuration independent of process CWD."""
    api_root = Path(__file__).resolve().parents[1]
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(migrations_dir))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations_upgrade(database_url: str, revision: str = "head") -> None:
    """Apply Alembic database migrations up to ``revision``."""
    cfg = build_alembic_config(database_url)
    command.upgrade(cfg, revision)


def run_migrations_downgrade(database_url: str, revision: str = "base") -> None:
    """Revert Alembic database migrations down to ``revision``."""
    cfg = build_alembic_config(database_url)
    command.downgrade(cfg, revision)
