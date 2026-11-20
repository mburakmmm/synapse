"""SQLAlchemy ORM models for protocols, experiments, durable jobs, and audit logs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Shared SQLAlchemy 2.0 declarative base."""


class ProtocolRevisionRecord(Base):
    """Tracked protocol revisions, including frozen immutable hashes."""

    __tablename__ = "protocol_revisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    protocol_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_intent: Mapped[str] = mapped_column(String(32), nullable=False)
    protocol_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    frozen_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ExperimentRecord(Base):
    """Logical experiment record binding protocol revision and target dataset."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    protocol_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    protocol_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dataset_release: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class JobRecord(Base):
    """Durable background job queue row with idempotency, worker lease, and cancellation."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at_utc"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("experiments.id"), nullable=True
    )
    parent_job_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("jobs.id"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_expires_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventRecord(Base):
    """Append-only audit log recording protocol freezes, job transitions, and recoveries."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
