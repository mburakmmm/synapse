"""Initial metadata, durable jobs, and audit schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "protocol_revisions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("protocol_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analysis_intent", sa.String(length=32), nullable=False),
        sa.Column("protocol_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("frozen_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("protocol_sha256", name="uq_protocol_revisions_sha256"),
    )
    op.create_index(
        "ix_protocol_revisions_protocol_id",
        "protocol_revisions",
        ["protocol_id"],
    )

    op.create_table(
        "experiments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("protocol_id", sa.String(length=128), nullable=False),
        sa.Column("protocol_revision", sa.Integer(), nullable=False),
        sa.Column("protocol_sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_release", sa.String(length=64), nullable=False),
        sa.Column("condition_summary_json", sa.Text(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experiments_protocol_id", "experiments", ["protocol_id"])
    op.create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("experiment_id", sa.String(length=64), sa.ForeignKey("experiments.id")),
        sa.Column("parent_job_id", sa.String(length=64), sa.ForeignKey("jobs.id")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("worker_pid", sa.Integer(), nullable=True),
        sa.Column("lease_expires_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_status_created", "jobs", ["status", "created_at_utc"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_audit_events_created_at_utc", "audit_events", ["created_at_utc"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at_utc", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_jobs_status_created", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_experiments_dataset_id", table_name="experiments")
    op.drop_index("ix_experiments_protocol_id", table_name="experiments")
    op.drop_table("experiments")

    op.drop_index("ix_protocol_revisions_protocol_id", table_name="protocol_revisions")
    op.drop_table("protocol_revisions")
