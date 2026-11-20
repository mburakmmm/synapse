"""Versioned FastAPI application factory exposing SYNAPSE /api/v1 endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import APIRouter, FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select

from synapse_api.config import Settings
from synapse_api.db import create_db_engine, make_session_factory, run_migrations_upgrade
from synapse_api.jobs import record_audit_event, request_cancel_job, retry_failed_job, submit_job
from synapse_api.models import AuditEventRecord, JobRecord, ProtocolRevisionRecord
from synapse_api.schemas import (
    ExperimentPlanRequest,
    JobSubmitRequest,
    ModelValidationRequest,
    ProtocolFreezeRequest,
    ProtocolValidateRequest,
    SubgraphQueryRequest,
)
from synapse_api.security import InvalidIdentifierError, PathContainmentError
from synapse_api.service import (
    ResourceNotFoundError,
    ServiceValidationError,
    build_validated_job_payload,
    create_experiment_record,
    freeze_protocol_request,
    get_analysis_detail,
    get_dataset_plan,
    get_run_detail,
    inspect_dataset_graph,
    list_analyses,
    list_benchmarks,
    list_dataset_neurons,
    list_datasets,
    list_exports,
    list_models_and_backends,
    list_protocols,
    list_runs,
    plan_experiment_request,
    query_dataset_subgraph,
    resolve_export_file,
    resolve_run_artifact,
    serialize_audit_event,
    serialize_job,
    serialize_protocol_revision,
    validate_model_payload,
    validate_protocol_request,
)
from synapse_core import DirectedConnectomeGraph, SubgraphBoundExceededError
from synapse_experiments import ProtocolValidationError


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def create_app(settings: Settings | None = None, *, run_migrations: bool = True) -> FastAPI:
    """Create configured SYNAPSE FastAPI application bound cleanly to local settings."""
    cfg = Settings.from_env() if settings is None else settings
    if run_migrations:
        run_migrations_upgrade(cfg.database_url)

    engine = create_db_engine(cfg.database_url)
    session_factory = make_session_factory(engine)
    graph_cache: dict[tuple[str, str], DirectedConnectomeGraph] = {}

    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="SYNAPSE Research Laboratory API",
        version="1.0.0",
        description="Local-first reproducible computational neuroscience API (Research Use Only)",
        lifespan=_lifespan,
    )
    app.state.settings = cfg
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cfg.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.exception_handler(PathContainmentError)
    def _handle_path_containment(_req: Request, exc: PathContainmentError) -> JSONResponse:
        return _error_response(403, "path_containment_violation", str(exc))

    @app.exception_handler(InvalidIdentifierError)
    def _handle_invalid_id(_req: Request, exc: InvalidIdentifierError) -> JSONResponse:
        return _error_response(400, "invalid_identifier", str(exc))

    @app.exception_handler(ResourceNotFoundError)
    def _handle_not_found(_req: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return _error_response(404, "not_found", str(exc))

    def _handle_validation_error(_req: Request, exc: Exception) -> JSONResponse:
        return _error_response(400, "validation_error", str(exc))

    for exc_type in (
        ProtocolValidationError,
        ServiceValidationError,
        SubgraphBoundExceededError,
        ValueError,
    ):
        app.add_exception_handler(exc_type, _handle_validation_error)

    v1 = APIRouter(prefix="/api/v1")

    @v1.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "api_version": "v1",
            "ruo_notice": "Research Use Only (RUO) - not for clinical or diagnostic use",
            "bind_host": cfg.bind_host,
        }

    @v1.get("/datasets")
    def get_datasets() -> dict[str, Any]:
        return list_datasets(cfg)

    @v1.get("/datasets/{dataset_id}/plan")
    def dataset_plan(dataset_id: str) -> dict[str, Any]:
        return get_dataset_plan(dataset_id)

    @v1.get("/datasets/{dataset_id}/inspect")
    def dataset_inspect(dataset_id: str) -> dict[str, Any]:
        return inspect_dataset_graph(cfg, dataset_id, graph_cache=graph_cache)

    @v1.get("/datasets/{dataset_id}/neurons")
    def dataset_neurons(
        dataset_id: str,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=500),
        search: str | None = Query(default=None),
    ) -> dict[str, Any]:
        return list_dataset_neurons(
            cfg,
            dataset_id,
            offset=offset,
            limit=limit,
            search=search,
        )

    @v1.post("/datasets/{dataset_id}/subgraph")
    def dataset_subgraph(dataset_id: str, body: SubgraphQueryRequest) -> dict[str, Any]:
        return query_dataset_subgraph(
            cfg,
            dataset_id,
            seed_neuron_ids=body.seed_neuron_ids,
            hops=body.hops,
            direction=body.direction,
            min_synapses=body.min_synapses,
            max_nodes=body.max_nodes,
            graph_cache=graph_cache,
        )

    @v1.get("/models")
    def models_list() -> dict[str, Any]:
        return list_models_and_backends()

    @v1.post("/models/validate")
    def models_validate(body: ModelValidationRequest) -> dict[str, Any]:
        return validate_model_payload(body.spec)

    @v1.get("/protocols")
    def protocols_list() -> dict[str, Any]:
        files_payload = list_protocols(cfg)
        with session_factory() as session:
            recs = (
                session.execute(
                    select(ProtocolRevisionRecord).order_by(
                        ProtocolRevisionRecord.created_at_utc.desc()
                    )
                )
                .scalars()
                .all()
            )
            files_payload["frozen_records"] = [serialize_protocol_revision(r) for r in recs]
        return files_payload

    @v1.post("/protocols/validate")
    def protocols_validate(body: ProtocolValidateRequest) -> dict[str, Any]:
        return validate_protocol_request(
            cfg,
            protocol_path=body.protocol_path,
            yaml_text=body.yaml_text,
            allow_unresolved=body.allow_unresolved,
        )

    @v1.post("/protocols/freeze")
    def protocols_freeze(body: ProtocolFreezeRequest) -> dict[str, Any]:
        frozen_path, doc, frozen_sha = freeze_protocol_request(
            cfg,
            protocol_path=body.protocol_path,
            out_filename=body.out_filename,
            confirmed=body.confirmed,
        )
        rel_path = frozen_path.relative_to(cfg.protocols_root).as_posix()
        with session_factory.begin() as session:
            existing = session.execute(
                select(ProtocolRevisionRecord).where(
                    ProtocolRevisionRecord.protocol_sha256 == frozen_sha
                )
            ).scalar_one_or_none()
            if existing is None:
                rec = ProtocolRevisionRecord(
                    id=f"prev_{uuid.uuid4().hex[:12]}",
                    protocol_id=str(doc["protocol_id"]),
                    revision=int(doc["revision"]),
                    status=str(doc["status"]),
                    analysis_intent=str(doc["analysis_intent"]),
                    protocol_sha256=frozen_sha,
                    file_path=rel_path,
                    frozen_at_utc=datetime.fromisoformat(str(doc["frozen_at_utc"])),
                )
                session.add(rec)
                session.flush()
                record_audit_event(
                    session,
                    actor="api",
                    action="protocol.frozen",
                    resource_type="protocol_revision",
                    resource_id=rec.id,
                    details={
                        "protocol_id": rec.protocol_id,
                        "revision": rec.revision,
                        "protocol_sha256": frozen_sha,
                        "file_path": rel_path,
                    },
                )
            else:
                rec = existing
            return {
                "frozen_path": rel_path,
                "record": serialize_protocol_revision(rec),
            }

    @v1.post("/experiments/plan")
    def experiments_plan(body: ExperimentPlanRequest) -> dict[str, Any]:
        return plan_experiment_request(
            cfg,
            protocol_path=body.protocol_path,
            dataset_id=body.dataset_id,
            replicates=body.replicates,
        )

    @v1.post("/jobs")
    def jobs_submit(
        body: JobSubmitRequest,
        idempotency_key_hdr: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> JSONResponse:
        idem_key = idempotency_key_hdr or body.idempotency_key
        resolved_payload, plan = build_validated_job_payload(
            cfg,
            kind=body.kind,
            raw_params=body.model_dump(),
        )
        with session_factory.begin() as session:
            experiment_id: str | None = None
            if plan is not None:
                exp = create_experiment_record(plan=plan)
                session.add(exp)
                session.flush()
                experiment_id = exp.id
            job, created = submit_job(
                session,
                kind=body.kind,
                payload=resolved_payload,
                idempotency_key=idem_key,
                experiment_id=experiment_id,
                actor="api",
            )
            body_out = {"created": created, "job": serialize_job(job)}
        return JSONResponse(status_code=201 if created else 200, content=body_out)

    @v1.get("/jobs")
    def jobs_list(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        status: str | None = Query(default=None),
    ) -> dict[str, Any]:
        with session_factory() as session:
            stmt = select(JobRecord).order_by(JobRecord.created_at_utc.desc())
            if status:
                stmt = stmt.where(JobRecord.status == status)
            all_rows = session.execute(stmt).scalars().all()
            total = len(all_rows)
            sliced = all_rows[offset : offset + limit]
            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "jobs": [serialize_job(j) for j in sliced],
            }

    @v1.get("/jobs/{job_id}")
    def jobs_get(job_id: str) -> dict[str, Any]:
        with session_factory() as session:
            job = session.get(JobRecord, job_id)
            if job is None:
                raise ResourceNotFoundError(f"Job not found: {job_id!r}")
            return {"job": serialize_job(job)}

    @v1.post("/jobs/{job_id}/cancel")
    def jobs_cancel(job_id: str) -> dict[str, Any]:
        with session_factory.begin() as session:
            if session.get(JobRecord, job_id) is None:
                raise ResourceNotFoundError(f"Job not found: {job_id!r}")
            job = request_cancel_job(session, job_id=job_id, actor="api")
            return {"job": serialize_job(job)}

    @v1.post("/jobs/{job_id}/retry")
    def jobs_retry(job_id: str) -> JSONResponse:
        with session_factory.begin() as session:
            if session.get(JobRecord, job_id) is None:
                raise ResourceNotFoundError(f"Job not found: {job_id!r}")
            new_job = retry_failed_job(session, job_id=job_id, actor="api")
            return JSONResponse(status_code=201, content={"job": serialize_job(new_job)})

    @v1.get("/runs")
    def runs_list(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
        condition_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ) -> dict[str, Any]:
        return list_runs(cfg, limit=limit, offset=offset, condition_id=condition_id, status=status)

    @v1.get("/runs/{run_id}")
    def runs_detail(run_id: str) -> dict[str, Any]:
        return get_run_detail(cfg, run_id)

    @v1.get("/runs/{run_id}/artifacts/{artifact_path:path}")
    def runs_artifact(run_id: str, artifact_path: str) -> FileResponse:
        resolved = resolve_run_artifact(cfg, run_id, artifact_path)
        return FileResponse(path=resolved, filename=resolved.name)

    @v1.get("/benchmarks")
    def benchmarks_list() -> dict[str, Any]:
        return list_benchmarks(cfg)

    @v1.get("/analyses")
    def analyses_list() -> dict[str, Any]:
        return list_analyses(cfg)

    @v1.get("/analyses/{analysis_key}")
    def analyses_detail(analysis_key: str) -> dict[str, Any]:
        return get_analysis_detail(cfg, analysis_key)

    @v1.get("/exports")
    def exports_list() -> dict[str, Any]:
        return list_exports(cfg)

    @v1.get("/exports/{export_key}/files/{file_path:path}")
    def exports_file(export_key: str, file_path: str) -> FileResponse:
        resolved = resolve_export_file(cfg, export_key, file_path)
        return FileResponse(path=resolved, filename=resolved.name)

    @v1.get("/audit")
    def audit_list(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        with session_factory() as session:
            all_events = (
                session.execute(select(AuditEventRecord).order_by(AuditEventRecord.id.desc()))
                .scalars()
                .all()
            )
            total = len(all_events)
            sliced = all_events[offset : offset + limit]
            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "events": [serialize_audit_event(ev) for ev in sliced],
            }

    app.include_router(v1)
    return app
