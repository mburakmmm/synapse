# ADR-0005: Phase 3 Research Laboratory Architecture (CLI, API, Worker, DB, Web UI)

- **Status:** Accepted (Phase 3 Baseline)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

Phase 3 promotes SYNAPSE from a CLI-only simulation pipeline to a full local-first computational research laboratory (`AGENTS.md` §4, §8, §9, §11, §13, §15) with protocol freezing, dry-run planning, statistical permutation/FDR/sensitivity checks, a durable metadata database + isolated subprocess worker, a versioned HTTP API (`/api/v1`), and an exploratory React UI—without duplicating numerical execution in the API or browser.

## Decision

1. **Strict Scientific Kernel Isolation (`packages/*` vs `apps/*`):**
   - Keep `packages/synapse_*` strictly free of FastAPI, Starlette, Uvicorn, SQLAlchemy, Alembic, and psycopg dependencies (enforced via AST test in [`test_import_boundaries.py`](../../tests/unit/test_import_boundaries.py)).
   - Place API orchestration in [`apps/api/synapse_api/`](../../apps/api/synapse_api/), isolated subprocess worker execution in [`apps/worker/synapse_worker/`](../../apps/worker/synapse_worker/), and the React/TypeScript/Vite/Plotly.js workbench in [`apps/web/`](../../apps/web/).
2. **Dual-Engine Metadata Persistence & Migrations (PostgreSQL + Local SQLite Default):**
   - Manage `protocol_revisions`, `experiments`, `jobs`, and `audit_events` through SQLAlchemy 2.0 ORM + Alembic migrations ([`0001_initial_schema.py`](../../apps/api/synapse_api/migrations/versions/0001_initial_schema.py)).
   - Support PostgreSQL (`FOR UPDATE SKIP LOCKED` queueing in [`compose.yaml`](../../compose.yaml)) and zero-setup local SQLite WAL (`sqlite:///runs/synapse_lab.sqlite3`) via atomic conditional `UPDATE` claiming (`claim_next_job`).
3. **Allowlisted Subprocess Execution, Lease Recovery, Cancellation, and Security Controls:**
   - Execute only three allowlisted job kinds (`protocol_experiment`, `analysis`, `export_bundle`) in clean Python subprocesses; disallow arbitrary script upload or untrusted pickle execution.
   - Bind HTTP/Postgres/Web listeners strictly to `127.0.0.1`, enforce regex ID checks + `resolve_within_root` path containment on all file/artifact routes, enforce idempotency keys on `POST /api/v1/jobs`, require deliberate confirmation to freeze a protocol (`--confirm-freeze` / `confirmed: true`), and link retries via `parent_job_id` without mutating failed attempts.
4. **Statistical Additions (`synapse_analysis.stats`) & Explicit GPU Unverified Status:**
   - Implement exact (`2^n` sign-flip when `n <= 14`) and seeded Monte Carlo paired permutation tests, Benjamini–Hochberg FDR q-values, and 1D local sensitivity summaries, cross-checked against `scipy.stats`.
   - Expose `brian2_cuda` strictly as `verified=false` / Linux CUDA opt-in; no unverified GPU support claimed on native Windows.

## Consequences

- CLI and API/worker execute identical scientific core entrypoints (`run_protocol_experiment`, `run_paired_analysis`, `export_evidence_bundle`).
- Frontend UI preserves 64-bit neuron identifiers as strings (`"9007199254740996"`, `"720575940660219265"`), visualizes real benchmark/paired-analysis results via Plotly.js, and displays explicit `RUO` and `SYNTHETIC FIXTURE` badges.
