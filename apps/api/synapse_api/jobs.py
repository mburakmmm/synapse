"""Transactional durable job queue operations, leases, cancellation, retries, and audit logs."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from synapse_api.models import AuditEventRecord, JobRecord, utcnow

ALLOWED_JOB_KINDS = frozenset({"protocol_experiment", "analysis", "export_bundle"})
TERMINAL_JOB_STATES = frozenset({"succeeded", "failed", "cancelled"})


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def record_audit_event(
    session: Session,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any] | None = None,
) -> AuditEventRecord:
    """Append an immutable audit log entry within the caller's transaction."""
    event = AuditEventRecord(
        created_at_utc=utcnow(),
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=json.dumps(details or {}, sort_keys=True),
    )
    session.add(event)
    session.flush()
    return event


def submit_job(
    session: Session,
    *,
    kind: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    experiment_id: str | None = None,
    parent_job_id: str | None = None,
    attempt_number: int = 1,
    actor: str = "api",
) -> tuple[JobRecord, bool]:
    """Enqueue a validated allowlisted job, enforcing idempotency-key deduplication."""
    if kind not in ALLOWED_JOB_KINDS:
        raise ValueError(f"Unsupported job kind {kind!r}; allowed: {sorted(ALLOWED_JOB_KINDS)}")

    if idempotency_key is not None:
        existing = session.execute(
            select(JobRecord).where(JobRecord.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False

    job = JobRecord(
        id=f"job_{uuid.uuid4().hex[:12]}",
        experiment_id=experiment_id,
        parent_job_id=parent_job_id,
        idempotency_key=idempotency_key,
        kind=kind,
        status="queued",
        attempt_number=attempt_number,
        payload_json=json.dumps(payload, sort_keys=True),
        created_at_utc=utcnow(),
    )
    session.add(job)
    session.flush()
    record_audit_event(
        session,
        actor=actor,
        action="job.submitted",
        resource_type="job",
        resource_id=job.id,
        details={
            "kind": kind,
            "attempt_number": attempt_number,
            "parent_job_id": parent_job_id,
            "idempotency_key": idempotency_key,
        },
    )
    return job, True


def claim_next_job(
    session: Session,
    *,
    worker_id: str,
    lease_seconds: int = 300,
) -> JobRecord | None:
    """Atomically claim the oldest queued job using PostgreSQL skip-locked or SQLite CAS."""
    now = utcnow()
    lease_until = now + timedelta(seconds=lease_seconds)
    dialect_name = session.get_bind().dialect.name

    if dialect_name == "postgresql":
        job = (
            session.execute(
                select(JobRecord)
                .where(JobRecord.status == "queued")
                .order_by(JobRecord.created_at_utc.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            .scalars()
            .first()
        )
        if job is None:
            return None
        job.status = "preparing"
        job.worker_id = worker_id
        job.started_at_utc = now
        job.heartbeat_at_utc = now
        job.lease_expires_at_utc = lease_until
        session.flush()
        record_audit_event(
            session,
            actor=worker_id,
            action="job.claimed",
            resource_type="job",
            resource_id=job.id,
            details={"lease_seconds": lease_seconds},
        )
        return job

    candidates = (
        session.execute(
            select(JobRecord.id)
            .where(JobRecord.status == "queued")
            .order_by(JobRecord.created_at_utc.asc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    for job_id in candidates:
        stmt = (
            update(JobRecord)
            .where(JobRecord.id == job_id, JobRecord.status == "queued")
            .values(
                status="preparing",
                worker_id=worker_id,
                started_at_utc=now,
                heartbeat_at_utc=now,
                lease_expires_at_utc=lease_until,
            )
        )
        res = session.execute(stmt)
        if isinstance(res, CursorResult) and res.rowcount == 1:
            claimed = session.get(JobRecord, job_id)
            assert claimed is not None
            session.refresh(claimed)
            record_audit_event(
                session,
                actor=worker_id,
                action="job.claimed",
                resource_type="job",
                resource_id=job_id,
                details={"lease_seconds": lease_seconds},
            )
            return claimed
    return None


def heartbeat_job(
    session: Session,
    *,
    job_id: str,
    worker_id: str,
    worker_pid: int | None = None,
    lease_seconds: int = 300,
    new_status: str | None = None,
) -> JobRecord:
    """Extend a worker lease and optionally transition preparing -> running."""
    job = session.get(JobRecord, job_id)
    if job is None:
        raise ValueError(f"Unknown job_id: {job_id}")
    now = utcnow()
    job.heartbeat_at_utc = now
    job.lease_expires_at_utc = now + timedelta(seconds=lease_seconds)
    job.worker_id = worker_id
    if worker_pid is not None:
        job.worker_pid = worker_pid
    if new_status is not None and job.status not in ("cancel_requested", *TERMINAL_JOB_STATES):
        job.status = new_status
    session.flush()
    return job


def request_cancel_job(
    session: Session,
    *,
    job_id: str,
    actor: str = "api",
    reason: str = "Cancelled by user request",
) -> JobRecord:
    """Request cooperative subprocess cancellation or immediately cancel queued jobs."""
    job = session.get(JobRecord, job_id)
    if job is None:
        raise ValueError(f"Unknown job_id: {job_id}")
    if job.status in TERMINAL_JOB_STATES:
        return job
    if job.status == "queued":
        job.status = "cancelled"
        job.ended_at_utc = utcnow()
        job.error_message = reason
        session.flush()
        record_audit_event(
            session,
            actor=actor,
            action="job.cancelled",
            resource_type="job",
            resource_id=job.id,
            details={"reason": reason, "from_state": "queued"},
        )
        return job

    if job.status != "cancel_requested":
        prev = job.status
        job.status = "cancel_requested"
        job.error_message = reason
        session.flush()
        record_audit_event(
            session,
            actor=actor,
            action="job.cancel_requested",
            resource_type="job",
            resource_id=job.id,
            details={"reason": reason, "from_state": prev},
        )
    return job


def mark_job_state(
    session: Session,
    *,
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    actor: str = "worker",
) -> JobRecord:
    """Commit terminal or intermediate state transition with audit record."""
    job = session.get(JobRecord, job_id)
    if job is None:
        raise ValueError(f"Unknown job_id: {job_id}")
    prev = job.status
    job.status = status
    if result is not None:
        job.result_json = json.dumps(result, sort_keys=True)
    if error_message is not None:
        job.error_message = error_message
    if status in TERMINAL_JOB_STATES and job.ended_at_utc is None:
        job.ended_at_utc = utcnow()
    session.flush()
    record_audit_event(
        session,
        actor=actor,
        action=f"job.{status}",
        resource_type="job",
        resource_id=job.id,
        details={"from_state": prev, "error_message": error_message},
    )
    return job


def recover_expired_leases(
    session: Session,
    *,
    now_utc: datetime | None = None,
    actor: str = "worker_recovery",
) -> list[str]:
    """Fail jobs whose active worker leases have expired so they never remain stuck."""
    now = utcnow() if now_utc is None else _as_utc(now_utc)
    assert now is not None
    active_jobs = (
        session.execute(
            select(JobRecord).where(
                JobRecord.status.in_(("preparing", "running", "cancel_requested"))
            )
        )
        .scalars()
        .all()
    )
    expired_ids: list[str] = []
    for job in active_jobs:
        lease_exp = _as_utc(job.lease_expires_at_utc)
        if lease_exp is not None and lease_exp < now:
            prev = job.status
            job.status = "failed"
            job.ended_at_utc = now
            job.error_message = "Worker lease expired before completion"
            expired_ids.append(job.id)
            record_audit_event(
                session,
                actor=actor,
                action="job.lease_expired",
                resource_type="job",
                resource_id=job.id,
                details={"from_state": prev, "worker_id": job.worker_id},
            )
    session.flush()
    return expired_ids


def retry_failed_job(
    session: Session,
    *,
    job_id: str,
    actor: str = "api",
) -> JobRecord:
    """Create a new queued attempt linked to an existing failed or cancelled job."""
    orig = session.get(JobRecord, job_id)
    if orig is None:
        raise ValueError(f"Unknown job_id: {job_id}")
    if orig.status not in ("failed", "cancelled"):
        raise ValueError(
            f"Only failed or cancelled jobs can be retried; got status={orig.status!r}"
        )
    payload = json.loads(orig.payload_json)
    new_job, _ = submit_job(
        session,
        kind=orig.kind,
        payload=payload,
        experiment_id=orig.experiment_id,
        parent_job_id=orig.id,
        attempt_number=orig.attempt_number + 1,
        actor=actor,
    )
    record_audit_event(
        session,
        actor=actor,
        action="job.retried",
        resource_type="job",
        resource_id=new_job.id,
        details={"parent_job_id": orig.id, "attempt_number": new_job.attempt_number},
    )
    return new_job
