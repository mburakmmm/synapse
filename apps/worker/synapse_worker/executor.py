"""Durable worker loop claiming PostgreSQL/SQLite jobs into bounded subprocesses."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from synapse_api.config import Settings
from synapse_api.db import create_db_engine, make_session_factory, run_migrations_upgrade
from synapse_api.jobs import (
    claim_next_job,
    heartbeat_job,
    mark_job_state,
    recover_expired_leases,
)
from synapse_api.models import JobRecord
from synapse_experiments.job_control import (
    _terminate_process_tree,
    mark_incomplete_runs_cancelled,
)


class WorkerRunner:
    """Claims queued metadata-DB jobs and executes them inside isolated Python subprocesses."""

    def __init__(
        self,
        settings: Settings,
        *,
        worker_id: str | None = None,
        migrate_on_start: bool = True,
    ) -> None:
        self.settings = settings
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        if migrate_on_start:
            run_migrations_upgrade(settings.database_url)
        self.engine = create_db_engine(settings.database_url)
        self.session_factory = make_session_factory(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def run_once(
        self,
        *,
        timeout_s: float | None = None,
        poll_interval_s: float = 0.2,
    ) -> str | None:
        """Claim and execute at most one queued job, handling heartbeats, timeout, and cancel."""
        with self.session_factory.begin() as session:
            recover_expired_leases(session, actor=self.worker_id)
            job = claim_next_job(
                session,
                worker_id=self.worker_id,
                lease_seconds=self.settings.lease_seconds,
            )
            if job is None:
                return None
            job_id = job.id
            kind = job.kind
            payload = json.loads(job.payload_json)

        job_tmp_dir = self.settings.runs_root / "_worker_tmp" / job_id
        job_tmp_dir.mkdir(parents=True, exist_ok=True)
        job_file = job_tmp_dir / "job_input.json"
        result_file = job_tmp_dir / "job_result.json"
        log_file = job_tmp_dir / "subprocess.log"

        spec = {
            "job_id": job_id,
            "kind": kind,
            "payload": payload,
            "result_file": str(result_file),
        }
        job_file.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")

        popen_kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True

        cmd = [
            sys.executable,
            "-m",
            "synapse_worker.subprocess_entry",
            "--job-file",
            str(job_file),
        ]

        t_start = time.monotonic()
        max_timeout = (
            float(self.settings.job_timeout_seconds) if timeout_s is None else float(timeout_s)
        )

        with log_file.open("w", encoding="utf-8") as log_fh:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.settings.repo_root),
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                close_fds=True,
                **popen_kwargs,
            )

        with self.session_factory.begin() as session:
            heartbeat_job(
                session,
                job_id=job_id,
                worker_id=self.worker_id,
                worker_pid=proc.pid,
                lease_seconds=self.settings.lease_seconds,
                new_status="running",
            )

        cancelled = False
        timed_out = False
        while True:
            try:
                proc.wait(timeout=poll_interval_s)
                break
            except subprocess.TimeoutExpired:
                pass

            with self.session_factory.begin() as session:
                current = session.get(JobRecord, job_id)
                if current is not None and current.status == "cancel_requested":
                    cancelled = True
                else:
                    heartbeat_job(
                        session,
                        job_id=job_id,
                        worker_id=self.worker_id,
                        worker_pid=proc.pid,
                        lease_seconds=self.settings.lease_seconds,
                    )

            if cancelled:
                _terminate_process_tree(proc.pid)
                proc.wait(timeout=5.0)
                break

            if (time.monotonic() - t_start) > max_timeout:
                timed_out = True
                _terminate_process_tree(proc.pid)
                proc.wait(timeout=5.0)
                break

        with self.session_factory.begin() as session:
            current = session.get(JobRecord, job_id)
            if cancelled or (current is not None and current.status == "cancel_requested"):
                if kind == "protocol_experiment" and "runs_dir" in payload:
                    mark_incomplete_runs_cancelled(
                        Path(payload["runs_dir"]),
                        reason="Cancelled via durable worker",
                    )
                mark_job_state(
                    session,
                    job_id=job_id,
                    status="cancelled",
                    error_message="Cancelled by user request",
                    actor=self.worker_id,
                )
            elif timed_out:
                if kind == "protocol_experiment" and "runs_dir" in payload:
                    mark_incomplete_runs_cancelled(
                        Path(payload["runs_dir"]),
                        reason=f"Worker exceeded timeout ({max_timeout:.1f}s)",
                    )
                mark_job_state(
                    session,
                    job_id=job_id,
                    status="failed",
                    error_message=f"Worker subprocess exceeded timeout of {max_timeout:.1f}s",
                    actor=self.worker_id,
                )
            elif proc.returncode == 0 and result_file.is_file():
                res_data = json.loads(result_file.read_text(encoding="utf-8"))
                mark_job_state(
                    session,
                    job_id=job_id,
                    status="succeeded",
                    result=res_data,
                    actor=self.worker_id,
                )
            else:
                tail = ""
                if log_file.is_file():
                    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    tail = " | ".join(lines[-5:]) if lines else ""
                mark_job_state(
                    session,
                    job_id=job_id,
                    status="failed",
                    error_message=(
                        f"Worker subprocess exited with code {proc.returncode}"
                        + (f": {tail}" if tail else "")
                    ),
                    actor=self.worker_id,
                )
        return job_id

    def run_loop(
        self,
        *,
        poll_interval_s: float = 0.5,
        timeout_s: float | None = None,
        max_jobs: int | None = None,
    ) -> int:
        """Poll continuously for queued jobs until stopped or ``max_jobs`` processed."""
        handled = 0
        while max_jobs is None or handled < max_jobs:
            jid = self.run_once(timeout_s=timeout_s)
            if jid is None:
                time.sleep(poll_interval_s)
                continue
            handled += 1
        return handled
