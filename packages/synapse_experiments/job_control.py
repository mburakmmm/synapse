"""Offline file-backed local job lifecycle, subprocess detachment, and cancellation."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from synapse_experiments.runner import plan_protocol_experiment, run_protocol_experiment

TERMINAL_JOB_STATES = frozenset({"succeeded", "failed", "cancelled"})


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _proc_stat_is_dead(stat_line: str) -> bool:
    """Return True if a Linux /proc/<pid>/stat line reports a zombie or dead task."""
    rparen = stat_line.rfind(")")
    if rparen == -1:
        return False
    rest = stat_line[rparen + 1 :].lstrip()
    if not rest:
        return False
    return rest[0] in {"Z", "X", "x"}


def _is_linux_zombie(pid: int, *, proc_root: Path | None = None) -> bool:
    """Check /proc/<pid>/stat on Linux so un-reaped zombie children do not appear alive."""
    if proc_root is None:
        if not sys.platform.startswith("linux"):
            return False
        proc_root = Path("/proc")
    stat_path = proc_root / str(pid) / "stat"
    try:
        stat_line = stat_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return _proc_stat_is_dead(stat_line)


def _pid_is_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    if os.name == "nt":
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in proc.stdout
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return not _is_linux_zombie(pid)


def _terminate_process_tree(pid: int | None) -> None:
    if pid is None or pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
        return
    killpg_fn = getattr(os, "killpg", None)
    sent = False
    if killpg_fn is not None:
        try:
            killpg_fn(pid, signal.SIGTERM)
            sent = True
        except OSError:
            pass
    if not sent:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)

    term_deadline = time.monotonic() + 0.5
    while time.monotonic() < term_deadline and _pid_is_alive(pid):
        time.sleep(0.02)

    sigkill = getattr(signal, "SIGKILL", None)
    if sigkill is not None and _pid_is_alive(pid):
        killed = False
        if killpg_fn is not None:
            try:
                killpg_fn(pid, sigkill)
                killed = True
            except OSError:
                pass
        if not killed:
            with contextlib.suppress(OSError):
                os.kill(pid, sigkill)
        kill_deadline = time.monotonic() + 0.25
        while time.monotonic() < kill_deadline and _pid_is_alive(pid):
            time.sleep(0.02)


def _reap_detached_child(pid: int | None) -> None:
    """Reap a direct detached child on POSIX without affecting non-child or Windows PIDs."""
    if pid is None or pid <= 0 or os.name == "nt":
        return
    waitpid_fn = getattr(os, "waitpid", None)
    wnohang = getattr(os, "WNOHANG", 1)
    if waitpid_fn is None:
        return
    deadline = time.monotonic() + 0.25
    while True:
        try:
            waited_pid, _ = waitpid_fn(pid, wnohang)
        except OSError:
            return
        if waited_pid != 0 or time.monotonic() >= deadline:
            return
        time.sleep(0.01)


def mark_incomplete_runs_cancelled(runs_dir: Path, *, reason: str) -> list[str]:
    """Mark any run directory without a COMPLETE marker as cancelled while preserving artifacts."""
    cancelled_run_ids: list[str] = []
    if not runs_dir.is_dir():
        return cancelled_run_ids
    now_iso = datetime.now(UTC).isoformat()
    for candidate in sorted(runs_dir.iterdir()):
        if not candidate.is_dir() or (candidate / "COMPLETE").is_file():
            continue
        manifest_path = candidate / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        if manifest.get("status") in ("succeeded", "failed", "cancelled"):
            continue
        manifest["status"] = "cancelled"
        manifest["ended_at_utc"] = now_iso
        manifest["failure_reason"] = reason
        _write_json_atomic(manifest_path, manifest)
        cancelled_run_ids.append(str(manifest.get("run_id", candidate.name)))
    return cancelled_run_ids


def start_local_job(
    protocol_path: Path,
    dataset_dir: Path,
    work_dir: Path,
    *,
    replicates_override: int | None = None,
    workers: int = 1,
    detach: bool = False,
) -> dict[str, Any]:
    """Plan, enqueue, and launch an isolated subprocess run under ``work_dir``."""
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    plan = plan_protocol_experiment(
        protocol_path,
        dataset_dir,
        replicates_override=replicates_override,
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = work_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    spec_path = work_dir / "job_spec.json"
    state_path = work_dir / "job_state.json"
    log_path = work_dir / "worker.log"

    spec = {
        "job_id": job_id,
        "protocol_path": str(protocol_path.resolve()),
        "dataset_dir": str(dataset_dir.resolve()),
        "runs_dir": str(runs_dir.resolve()),
        "replicates_override": replicates_override,
        "workers": int(workers),
        "protocol_id": plan["protocol_id"],
        "protocol_revision": plan["protocol_revision"],
        "protocol_sha256": plan["protocol_sha256"],
        "dataset_id": plan["dataset_id"],
        "is_synthetic_fixture": plan["is_synthetic_fixture"],
    }
    _write_json_atomic(spec_path, spec)

    initial_state: dict[str, Any] = {
        "job_id": job_id,
        "status": "queued",
        "pid": None,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "started_at_utc": None,
        "ended_at_utc": None,
        "protocol_id": plan["protocol_id"],
        "protocol_sha256": plan["protocol_sha256"],
        "dataset_id": plan["dataset_id"],
        "is_synthetic_fixture": plan["is_synthetic_fixture"],
        "runs_dir": str(runs_dir),
        "total_planned_runs": plan["total_runs"],
        "run_dirs": [],
        "error": None,
    }
    _write_json_atomic(state_path, initial_state)

    cmd = [
        sys.executable,
        "-m",
        "synapse_experiments.job_control",
        "--spec-file",
        str(spec_path),
    ]
    popen_kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    with log_path.open("a", encoding="utf-8") as log_fh:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            close_fds=True,
            **popen_kwargs,
        )

    state_after_spawn = _read_json(state_path)
    if state_after_spawn.get("pid") is None and state_after_spawn.get("status") == "queued":
        state_after_spawn["pid"] = proc.pid
        _write_json_atomic(state_path, state_after_spawn)

    if detach:
        return _read_json(state_path)

    rc = proc.wait()
    final_state = _read_json(state_path)
    if rc != 0 or final_state.get("status") != "succeeded":
        raise RuntimeError(
            f"Local job {job_id} ended with status={final_state.get('status')}: "
            f"{final_state.get('error')}"
        )
    return final_state


def get_local_job_status(work_dir: Path) -> dict[str, Any]:
    """Read current job status, child process liveness, and partial/completed run states."""
    state_path = work_dir / "job_state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"No job_state.json found in {work_dir}")
    state = _read_json(state_path)
    pid = state.get("pid")
    alive = _pid_is_alive(int(pid) if pid is not None else None)

    runs_dir = Path(state["runs_dir"])
    runs_summary: list[dict[str, Any]] = []
    if runs_dir.is_dir():
        for candidate in sorted(runs_dir.iterdir()):
            if not candidate.is_dir():
                continue
            m_path = candidate / "manifest.json"
            if m_path.is_file():
                m = _read_json(m_path)
                runs_summary.append(
                    {
                        "run_id": m.get("run_id", candidate.name),
                        "condition_id": m.get("condition_id"),
                        "replicate_id": m.get("replicate_id"),
                        "status": m.get("status"),
                        "complete_marker": (candidate / "COMPLETE").is_file(),
                    }
                )
    return {
        **state,
        "process_alive": alive,
        "runs": runs_summary,
    }


def cancel_local_job(
    work_dir: Path,
    *,
    reason: str = "Cancelled by user request",
) -> dict[str, Any]:
    """Cancel a queued or running local job, terminate child processes, and mark incomplete runs."""
    state_path = work_dir / "job_state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"No job_state.json found in {work_dir}")
    state = _read_json(state_path)
    current_status = state.get("status")
    if current_status in TERMINAL_JOB_STATES:
        return {**state, "already_terminal": True}

    state["status"] = "cancel_requested"
    _write_json_atomic(state_path, state)

    pid = state.get("pid")
    pid_int = int(pid) if pid is not None else None
    _terminate_process_tree(pid_int)
    _reap_detached_child(pid_int)

    runs_dir = Path(state["runs_dir"])
    cancelled_runs = mark_incomplete_runs_cancelled(runs_dir, reason=reason)

    now_iso = datetime.now(UTC).isoformat()
    state["status"] = "cancelled"
    state["ended_at_utc"] = now_iso
    state["error"] = reason
    state["cancelled_incomplete_runs"] = cancelled_runs
    _write_json_atomic(state_path, state)
    return {**state, "already_terminal": False}


def _run_subprocess_entry(spec_file: Path) -> int:
    spec = _read_json(spec_file)
    work_dir = spec_file.parent
    state_path = work_dir / "job_state.json"
    runs_dir = Path(spec["runs_dir"])

    def _update_state(**updates: Any) -> dict[str, Any]:
        cur = _read_json(state_path)
        if cur.get("status") in ("cancel_requested", "cancelled"):
            return cur
        cur.update(updates)
        _write_json_atomic(state_path, cur)
        return cur

    _update_state(
        status="preparing",
        pid=os.getpid(),
        started_at_utc=datetime.now(UTC).isoformat(),
    )
    try:
        _update_state(status="running", pid=os.getpid())
        run_dirs = run_protocol_experiment(
            protocol_path=Path(spec["protocol_path"]),
            dataset_dir=Path(spec["dataset_dir"]),
            runs_dir=runs_dir,
            replicates_override=spec.get("replicates_override"),
            workers=int(spec.get("workers", 1)),
        )
        cur = _read_json(state_path)
        if cur.get("status") in ("cancel_requested", "cancelled"):
            return 130
        _update_state(
            status="succeeded",
            ended_at_utc=datetime.now(UTC).isoformat(),
            run_dirs=[str(p) for p in run_dirs],
            error=None,
        )
        return 0
    except Exception as exc:
        cur = _read_json(state_path)
        if cur.get("status") in ("cancel_requested", "cancelled"):
            return 130
        _update_state(
            status="failed",
            ended_at_utc=datetime.now(UTC).isoformat(),
            error=f"{type(exc).__name__}: {exc}",
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SYNAPSE local job worker entrypoint")
    parser.add_argument("--spec-file", required=True)
    args = parser.parse_args()
    return _run_subprocess_entry(Path(args.spec_file))


if __name__ == "__main__":
    raise SystemExit(main())
