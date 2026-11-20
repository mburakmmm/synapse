"""Environment-backed runtime settings for SYNAPSE API and durable worker."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable configuration loaded from environment variables with safe local-first defaults."""

    repo_root: Path
    database_url: str
    data_root: Path
    runs_root: Path
    protocols_root: Path
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    lease_seconds: int = 300
    job_timeout_seconds: int = 1800

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> Settings:
        root = (
            Path(__file__).resolve().parents[3] if repo_root is None else Path(repo_root).resolve()
        )
        data_env = os.environ.get("SYNAPSE_DATA_DIR")
        runs_env = os.environ.get("SYNAPSE_RUNS_DIR")
        protocols_env = os.environ.get("SYNAPSE_PROTOCOLS_DIR")

        data_root = (root / "data") if not data_env else _resolve_dir(root, data_env)
        runs_root = (root / "runs") if not runs_env else _resolve_dir(root, runs_env)
        protocols_root = (
            (root / "research" / "protocols")
            if not protocols_env
            else _resolve_dir(root, protocols_env)
        )

        default_sqlite = (runs_root / "synapse_lab.sqlite3").as_posix()
        db_url = os.environ.get("SYNAPSE_DATABASE_URL", f"sqlite:///{default_sqlite}")
        raw_cors = os.environ.get(
            "SYNAPSE_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
        cors = tuple(item.strip() for item in raw_cors.split(",") if item.strip())

        return cls(
            repo_root=root,
            database_url=db_url,
            data_root=data_root,
            runs_root=runs_root,
            protocols_root=protocols_root,
            cors_origins=cors,
            bind_host=os.environ.get("SYNAPSE_API_HOST", "127.0.0.1"),
            bind_port=int(os.environ.get("SYNAPSE_API_PORT", "8000")),
            lease_seconds=int(os.environ.get("SYNAPSE_WORKER_LEASE_SECONDS", "300")),
            job_timeout_seconds=int(os.environ.get("SYNAPSE_JOB_TIMEOUT_SECONDS", "1800")),
        )


def _resolve_dir(root: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    return p.resolve() if p.is_absolute() else (root / p).resolve()
