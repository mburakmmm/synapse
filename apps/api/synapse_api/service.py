"""Domain service layer connecting FastAPI routes strictly to SYNAPSE core packages."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import polars as pl

from synapse_api.config import Settings
from synapse_api.models import AuditEventRecord, ExperimentRecord, JobRecord, ProtocolRevisionRecord
from synapse_api.security import resolve_within_root, validate_identifier
from synapse_core import (
    Brian2CPUBackend,
    DirectedConnectomeGraph,
    LIFParameters,
    extract_bounded_subgraph,
    validate_model_spec,
)
from synapse_data import build_default_registry, validate_canonical_dataset
from synapse_experiments import (
    freeze_protocol,
    load_and_validate_protocol,
    load_graph_from_dataset,
    plan_protocol_experiment,
)
from synapse_experiments.protocol import ProtocolValidationError


class ResourceNotFoundError(LookupError):
    """Raised when a requested dataset, run, analysis, export, or job does not exist."""


class ServiceValidationError(ValueError):
    """Raised when an API input fails scientific, schema, or containment rules."""


def _find_curated_dataset_dirs(data_root: Path) -> dict[str, Path]:
    """Discover validated canonical dataset directories under ``data_root``."""
    found: dict[str, Path] = {}
    if not data_root.is_dir():
        return found
    for manifest_file in sorted(data_root.rglob("dataset_manifest.json")):
        if manifest_file.parent.name == "curated":
            continue
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        did = str(manifest.get("dataset_id", "")).strip()
        if did and did not in found:
            found[did] = manifest_file.parent
    return found


def list_datasets(settings: Settings) -> dict[str, Any]:
    """List registered biological sources plus discovered curated/fixture datasets."""
    reg = build_default_registry()
    on_disk = _find_curated_dataset_dirs(settings.data_root)
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for did in reg.list_dataset_ids():
        seen_ids.add(did)
        info = dict(reg.get(did).discover())
        info["on_disk"] = did in on_disk
        if did in on_disk:
            manifest = json.loads((on_disk[did] / "dataset_manifest.json").read_text("utf-8"))
            info["is_synthetic_fixture"] = bool(manifest["is_synthetic_fixture"])
            info["quality_report"] = manifest["quality_report"]
        items.append(info)

    for did, ds_dir in sorted(on_disk.items()):
        if did in seen_ids:
            continue
        manifest = json.loads((ds_dir / "dataset_manifest.json").read_text("utf-8"))
        items.append(
            {
                "dataset_id": did,
                "release": manifest["release"],
                "species": manifest["species"],
                "sex": manifest["sex"],
                "specimen_id": manifest["specimen_id"],
                "is_synthetic_fixture": bool(manifest["is_synthetic_fixture"]),
                "on_disk": True,
                "quality_report": manifest["quality_report"],
                "known_limitations": manifest["known_limitations"],
            }
        )
    return {"datasets": items}


def get_dataset_plan(dataset_id: str) -> dict[str, Any]:
    validate_identifier(dataset_id, "dataset_id")
    reg = build_default_registry()
    if dataset_id not in reg.list_dataset_ids():
        raise ResourceNotFoundError(f"Unknown registered dataset_id: {dataset_id!r}")
    return reg.get(dataset_id).plan().to_dict()


def resolve_dataset_dir(settings: Settings, dataset_id: str) -> Path:
    validate_identifier(dataset_id, "dataset_id")
    on_disk = _find_curated_dataset_dirs(settings.data_root)
    if dataset_id not in on_disk:
        raise ResourceNotFoundError(
            f"Canonical dataset {dataset_id!r} is not normalized under {settings.data_root}"
        )
    return on_disk[dataset_id]


def inspect_dataset_graph(
    settings: Settings,
    dataset_id: str,
    graph_cache: dict[tuple[str, str], DirectedConnectomeGraph] | None = None,
) -> dict[str, Any]:
    ds_dir = resolve_dataset_dir(settings, dataset_id)
    manifest = validate_canonical_dataset(ds_dir)
    graph = _load_cached_graph(ds_dir, graph_cache)
    return {
        "dataset_id": graph.dataset_id,
        "release": graph.release,
        "specimen_id": graph.specimen_id,
        "is_synthetic_fixture": graph.is_synthetic_fixture,
        "n_neurons": graph.n_neurons,
        "n_edges": graph.n_edges,
        "total_synapses": graph.total_synapses,
        "graph_sha256": graph.graph_sha256(),
        "orientation": "row=post_idx(target), col=pre_idx(source)",
        "quality_report": manifest["quality_report"],
        "known_limitations": manifest["known_limitations"],
    }


def _load_cached_graph(
    ds_dir: Path,
    graph_cache: dict[tuple[str, str], DirectedConnectomeGraph] | None,
) -> DirectedConnectomeGraph:
    manifest_text = (ds_dir / "dataset_manifest.json").read_text(encoding="utf-8")
    key = (str(ds_dir), str(hash(manifest_text)))
    if graph_cache is not None and key in graph_cache:
        return graph_cache[key]
    graph, _, _ = load_graph_from_dataset(ds_dir)
    if graph_cache is not None:
        graph_cache.clear()
        graph_cache[key] = graph
    return graph


def list_dataset_neurons(
    settings: Settings,
    dataset_id: str,
    *,
    offset: int = 0,
    limit: int = 50,
    search: str | None = None,
) -> dict[str, Any]:
    ds_dir = resolve_dataset_dir(settings, dataset_id)
    manifest = validate_canonical_dataset(ds_dir)
    neurons_scan = pl.scan_parquet(ds_dir / "curated" / "neurons.parquet")
    nts_scan = pl.scan_parquet(ds_dir / "curated" / "neurotransmitters.parquet").select(
        ["source_neuron_id", "neurotransmitter", "confidence"]
    )
    joined = neurons_scan.join(nts_scan, on="source_neuron_id", how="left")
    if search and search.strip():
        needle = search.strip().lower()
        joined = joined.filter(
            pl.col("source_neuron_id").str.to_lowercase().str.contains(needle, literal=True)
            | pl.col("cell_type")
            .fill_null("")
            .str.to_lowercase()
            .str.contains(needle, literal=True)
            | pl.col("region").fill_null("").str.to_lowercase().str.contains(needle, literal=True)
        )
    total = int(joined.select(pl.len()).collect().item())
    rows_df = joined.slice(offset, limit).collect()
    rows: list[dict[str, Any]] = []
    for row in rows_df.iter_rows(named=True):
        row_copy = dict(row)
        row_copy["source_neuron_id"] = str(row_copy["source_neuron_id"])
        rows.append(row_copy)
    return {
        "dataset_id": str(manifest["dataset_id"]),
        "release": str(manifest["release"]),
        "is_synthetic_fixture": bool(manifest["is_synthetic_fixture"]),
        "total": total,
        "offset": offset,
        "limit": limit,
        "neurons": rows,
    }


def query_dataset_subgraph(
    settings: Settings,
    dataset_id: str,
    *,
    seed_neuron_ids: list[str],
    hops: int,
    direction: str,
    min_synapses: int,
    max_nodes: int,
    graph_cache: dict[tuple[str, str], DirectedConnectomeGraph] | None = None,
) -> dict[str, Any]:
    ds_dir = resolve_dataset_dir(settings, dataset_id)
    graph = _load_cached_graph(ds_dir, graph_cache)
    sub, meta = extract_bounded_subgraph(
        graph,
        seed_neuron_ids=seed_neuron_ids,
        hop_limit=hops,
        direction=direction,  # type: ignore[arg-type]
        min_synapse_threshold=min_synapses,
        max_nodes=max_nodes,
    )
    pre_idx, post_idx, counts = sub.edge_arrays()
    edges_preview = [
        {
            "pre_neuron_id": sub.neuron_ids[int(p)],
            "post_neuron_id": sub.neuron_ids[int(q)],
            "synapse_count": int(c),
        }
        for p, q, c in list(zip(pre_idx.tolist(), post_idx.tolist(), counts.tolist(), strict=True))[
            :500
        ]
    ]
    return {
        "metadata": meta.model_dump(mode="json"),
        "nodes": [
            {
                "source_neuron_id": nid,
                "neurotransmitter": nt,
                "is_seed": nid in seed_neuron_ids,
            }
            for nid, nt in zip(sub.neuron_ids, sub.neurotransmitters, strict=True)
        ],
        "edges": edges_preview,
        "edges_truncated": len(counts) > 500,
    }


def list_models_and_backends() -> dict[str, Any]:
    default_lif = LIFParameters()
    shiu_lif = LIFParameters.shiu2024_reference()
    cpu_caps = Brian2CPUBackend().capabilities()
    return {
        "models": [
            {
                "model_id": default_lif.model_id,
                "model_revision": default_lif.model_revision,
                "parameter_manifest_sha256": default_lif.canonical_sha256(),
                "solver": default_lif.solver,
                "dt_s": default_lif.dt_s,
                "dg_unless_refractory": default_lif.dg_unless_refractory,
                "parameter_source": default_lif.parameter_source,
            },
            {
                "model_id": shiu_lif.model_id,
                "model_revision": shiu_lif.model_revision,
                "parameter_manifest_sha256": shiu_lif.canonical_sha256(),
                "solver": shiu_lif.solver,
                "dt_s": shiu_lif.dt_s,
                "dg_unless_refractory": shiu_lif.dg_unless_refractory,
                "parameter_source": shiu_lif.parameter_source,
            },
        ],
        "backends": [
            {
                "backend_id": cpu_caps.backend_id,
                "device": cpu_caps.device,
                "precision": cpu_caps.precision,
                "supported_solvers": list(cpu_caps.supported_solvers),
                "verified": True,
                "reproducibility_class": cpu_caps.reproducibility_class,
            },
            {
                "backend_id": "brian2_cuda",
                "device": "gpu",
                "precision": "float64",
                "supported_solvers": [],
                "verified": False,
                "reproducibility_class": "unverified_linux_opt_in_only",
            },
        ],
    }


def validate_model_payload(spec: dict[str, Any]) -> dict[str, Any]:
    raw_model = spec.get("model")
    target: dict[str, Any] = dict(raw_model) if isinstance(raw_model, dict) else spec
    return validate_model_spec(target)


def list_protocols(settings: Settings) -> dict[str, Any]:
    if not settings.protocols_root.is_dir():
        return {"protocols": []}
    protocols: list[dict[str, Any]] = []
    for yml_file in sorted(settings.protocols_root.rglob("*.yaml")):
        rel = yml_file.relative_to(settings.protocols_root).as_posix()
        try:
            doc, sha = load_and_validate_protocol(yml_file, require_executable=False)
            protocols.append(
                {
                    "relative_path": rel,
                    "protocol_id": doc["protocol_id"],
                    "revision": doc["revision"],
                    "status": doc["status"],
                    "analysis_intent": doc["analysis_intent"],
                    "protocol_sha256": sha,
                    "question": doc["question"],
                }
            )
        except Exception as exc:
            protocols.append(
                {
                    "relative_path": rel,
                    "status": "invalid",
                    "error": str(exc),
                }
            )
    return {"protocols": protocols}


def validate_protocol_request(
    settings: Settings,
    *,
    protocol_path: str | None,
    yaml_text: str | None,
    allow_unresolved: bool,
) -> dict[str, Any]:
    if bool(protocol_path) == bool(yaml_text):
        raise ServiceValidationError("Provide exactly one of 'protocol_path' or 'yaml_text'")

    if protocol_path is not None:
        resolved = resolve_within_root(settings.protocols_root, protocol_path)
        if not resolved.is_file():
            raise ResourceNotFoundError(f"Protocol file not found: {protocol_path!r}")
        doc, sha = load_and_validate_protocol(resolved, require_executable=not allow_unresolved)
    else:
        assert yaml_text is not None
        fd, tmp_name = tempfile.mkstemp(prefix="synapse_proto_", suffix=".yaml")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(yaml_text)
            doc, sha = load_and_validate_protocol(
                tmp_path,
                require_executable=not allow_unresolved,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    return {
        "valid": True,
        "protocol_id": doc["protocol_id"],
        "revision": doc["revision"],
        "protocol_status": doc["status"],
        "analysis_intent": doc["analysis_intent"],
        "executable": not allow_unresolved,
        "protocol_sha256": sha,
    }


def freeze_protocol_request(
    settings: Settings,
    *,
    protocol_path: str,
    out_filename: str | None,
    confirmed: bool,
) -> tuple[Path, dict[str, Any], str]:
    src = resolve_within_root(settings.protocols_root, protocol_path)
    if not src.is_file():
        raise ResourceNotFoundError(f"Protocol file not found: {protocol_path!r}")
    out_path = None
    if out_filename is not None:
        out_path = resolve_within_root(settings.protocols_root, out_filename)
    return freeze_protocol(src, out_path=out_path, confirmed=confirmed)


def plan_experiment_request(
    settings: Settings,
    *,
    protocol_path: str,
    dataset_id: str,
    replicates: int | None,
) -> dict[str, Any]:
    proto = resolve_within_root(settings.protocols_root, protocol_path)
    if not proto.is_file():
        raise ResourceNotFoundError(f"Protocol file not found: {protocol_path!r}")
    ds_dir = resolve_dataset_dir(settings, dataset_id)
    return plan_protocol_experiment(proto, ds_dir, replicates_override=replicates)


def build_validated_job_payload(
    settings: Settings,
    *,
    kind: str,
    raw_params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate and resolve sandboxed paths for queued jobs before persistence."""
    if kind == "protocol_experiment":
        proto_rel = raw_params.get("protocol_path")
        dataset_id = raw_params.get("dataset_id")
        if not proto_rel or not dataset_id:
            raise ServiceValidationError(
                "protocol_experiment requires 'protocol_path' and 'dataset_id'"
            )
        proto_path = resolve_within_root(settings.protocols_root, str(proto_rel))
        if not proto_path.is_file():
            raise ResourceNotFoundError(f"Protocol not found: {proto_rel!r}")
        ds_dir = resolve_dataset_dir(settings, str(dataset_id))
        replicates = raw_params.get("replicates")
        plan = plan_protocol_experiment(proto_path, ds_dir, replicates_override=replicates)
        work_name = raw_params.get("work_dir_name") or f"exp_{uuid.uuid4().hex[:8]}"
        validate_identifier(str(work_name), "work_dir_name")
        runs_dir = resolve_within_root(settings.runs_root, f"{work_name}/runs")
        resolved_payload = {
            "protocol_path": str(proto_path),
            "dataset_dir": str(ds_dir),
            "runs_dir": str(runs_dir),
            "replicates": replicates,
            "workers": int(raw_params.get("workers", 1)),
        }
        return resolved_payload, plan

    if kind == "analysis":
        runs_rel = raw_params.get("runs_rel_dir")
        out_rel = raw_params.get("out_rel_dir")
        b_cond = raw_params.get("baseline_condition")
        t_cond = raw_params.get("treatment_condition")
        nid = raw_params.get("target_neuron_id")
        if not all([runs_rel, out_rel, b_cond, t_cond, nid]):
            raise ServiceValidationError(
                "analysis job requires 'runs_rel_dir', 'out_rel_dir', 'baseline_condition', "
                "'treatment_condition', and 'target_neuron_id'"
            )
        runs_dir = resolve_within_root(settings.runs_root, str(runs_rel))
        out_dir = resolve_within_root(settings.runs_root, str(out_rel))
        return {
            "runs_dir": str(runs_dir),
            "out_dir": str(out_dir),
            "baseline_condition": str(b_cond),
            "treatment_condition": str(t_cond),
            "target_neuron_id": str(nid),
        }, None

    if kind == "export_bundle":
        analysis_rel = raw_params.get("analysis_rel_dir")
        out_rel = raw_params.get("out_rel_dir")
        if not analysis_rel or not out_rel:
            raise ServiceValidationError(
                "export_bundle job requires 'analysis_rel_dir' and 'out_rel_dir'"
            )
        analysis_dir = resolve_within_root(settings.runs_root, str(analysis_rel))
        out_dir = resolve_within_root(settings.runs_root, str(out_rel))
        return {
            "analysis_dir": str(analysis_dir),
            "out_dir": str(out_dir),
        }, None

    raise ServiceValidationError(f"Unsupported job kind: {kind!r}")


def _iter_run_manifests(runs_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not runs_root.is_dir():
        return found
    for m_path in sorted(runs_root.rglob("manifest.json")):
        if "_worker_tmp" in m_path.parts:
            continue
        try:
            data = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        run_id = str(data.get("run_id", "")).strip()
        if run_id and "protocol_id" in data:
            found[run_id] = (m_path.parent, data)
    return found


def list_runs(
    settings: Settings,
    *,
    limit: int = 50,
    offset: int = 0,
    condition_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    all_runs = _iter_run_manifests(settings.runs_root)
    rows: list[dict[str, Any]] = []
    for run_id, (r_dir, m) in all_runs.items():
        if condition_id and m.get("condition_id") != condition_id:
            continue
        if status and m.get("status") != status:
            continue
        rows.append(
            {
                "run_id": run_id,
                "status": m.get("status"),
                "complete_marker": (r_dir / "COMPLETE").is_file(),
                "protocol_id": m.get("protocol_id"),
                "protocol_revision": m.get("protocol_revision"),
                "condition_id": m.get("condition_id"),
                "replicate_id": m.get("replicate_id"),
                "dataset_id": m.get("dataset_id"),
                "model_id": m.get("model_id"),
                "is_synthetic_fixture": bool(m.get("is_synthetic_fixture", False)),
                "analysis_intent": m.get("analysis_intent"),
                "wall_seconds": (m.get("resource_usage") or {}).get("wall_seconds"),
                "failure_reason": m.get("failure_reason"),
                "relative_dir": r_dir.relative_to(settings.runs_root).as_posix(),
            }
        )
    rows.sort(key=lambda item: (str(item["protocol_id"]), str(item["run_id"])))
    total = len(rows)
    return {"total": total, "offset": offset, "limit": limit, "runs": rows[offset : offset + limit]}


def get_run_detail(settings: Settings, run_id: str) -> dict[str, Any]:
    validate_identifier(run_id, "run_id")
    all_runs = _iter_run_manifests(settings.runs_root)
    if run_id not in all_runs:
        raise ResourceNotFoundError(f"Run not found: {run_id!r}")
    r_dir, manifest = all_runs[run_id]
    metrics_preview: list[dict[str, Any]] = []
    metrics_pq = r_dir / "metrics.parquet"
    if metrics_pq.is_file():
        df = pl.read_parquet(metrics_pq).head(25)
        for row in df.iter_rows(named=True):
            row_copy = dict(row)
            row_copy["source_neuron_id"] = str(row_copy["source_neuron_id"])
            metrics_preview.append(row_copy)
    return {
        "run_id": run_id,
        "relative_dir": r_dir.relative_to(settings.runs_root).as_posix(),
        "complete_marker": (r_dir / "COMPLETE").is_file(),
        "manifest": manifest,
        "metrics_preview": metrics_preview,
    }


def resolve_run_artifact(settings: Settings, run_id: str, artifact_path: str) -> Path:
    validate_identifier(run_id, "run_id")
    all_runs = _iter_run_manifests(settings.runs_root)
    if run_id not in all_runs:
        raise ResourceNotFoundError(f"Run not found: {run_id!r}")
    run_dir, _ = all_runs[run_id]
    resolved = resolve_within_root(run_dir, artifact_path)
    if not resolved.is_file():
        raise ResourceNotFoundError(f"Artifact not found: {artifact_path!r}")
    return resolved


def list_benchmarks(settings: Settings) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    if settings.runs_root.is_dir():
        for b_path in sorted(settings.runs_root.rglob("benchmark_report.json")):
            try:
                data = json.loads(b_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            reports.append(
                {
                    "relative_path": b_path.relative_to(settings.runs_root).as_posix(),
                    "report": data,
                }
            )
    return {"benchmarks": reports}


def _iter_analyses(runs_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not runs_root.is_dir():
        return found
    for m_path in sorted(runs_root.rglob("analysis_manifest.json")):
        try:
            data = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = m_path.parent.relative_to(runs_root).as_posix()
        key = rel.replace("/", "__")
        found[key] = (m_path.parent, data)
    return found


def list_analyses(settings: Settings) -> dict[str, Any]:
    all_analyses = _iter_analyses(settings.runs_root)
    items = []
    for key, (a_dir, data) in all_analyses.items():
        items.append(
            {
                "analysis_key": key,
                "relative_dir": a_dir.relative_to(settings.runs_root).as_posix(),
                "target_neuron_id": str(data.get("target_neuron_id", "")),
                "baseline_condition": data.get("baseline_condition"),
                "treatment_condition": data.get("treatment_condition"),
                "failed_run_count": data.get("failed_run_count"),
                "provenance": data.get("provenance"),
                "paired_metrics": data.get("paired_metrics"),
            }
        )
    return {"analyses": items}


def get_analysis_detail(settings: Settings, analysis_key: str) -> dict[str, Any]:
    validate_identifier(analysis_key, "analysis_key")
    all_analyses = _iter_analyses(settings.runs_root)
    if analysis_key not in all_analyses:
        raise ResourceNotFoundError(f"Analysis not found: {analysis_key!r}")
    a_dir, manifest = all_analyses[analysis_key]
    pairs: list[dict[str, Any]] = []
    paired_pq = a_dir / "paired_differences.parquet"
    if paired_pq.is_file():
        df = pl.read_parquet(paired_pq)
        for row in df.iter_rows(named=True):
            row_copy = dict(row)
            row_copy["target_neuron_id"] = str(row_copy["target_neuron_id"])
            pairs.append(row_copy)
    return {
        "analysis_key": analysis_key,
        "manifest": manifest,
        "paired_differences": pairs,
    }


def _iter_exports(runs_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not runs_root.is_dir():
        return found
    for b_path in sorted(runs_root.rglob("bundle_manifest.json")):
        if b_path.parent.name != "provenance":
            continue
        bundle_root = b_path.parent.parent
        try:
            data = json.loads(b_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = bundle_root.relative_to(runs_root).as_posix()
        key = rel.replace("/", "__")
        found[key] = (bundle_root, data)
    return found


def list_exports(settings: Settings) -> dict[str, Any]:
    all_exports = _iter_exports(settings.runs_root)
    items = []
    for key, (b_root, manifest) in all_exports.items():
        files = [p.relative_to(b_root).as_posix() for p in sorted(b_root.rglob("*")) if p.is_file()]
        items.append(
            {
                "export_key": key,
                "relative_dir": b_root.relative_to(settings.runs_root).as_posix(),
                "is_synthetic_fixture": bool(manifest.get("is_synthetic_fixture", False)),
                "manifest": manifest,
                "files": files,
            }
        )
    return {"exports": items}


def resolve_export_file(settings: Settings, export_key: str, file_path: str) -> Path:
    validate_identifier(export_key, "export_key")
    all_exports = _iter_exports(settings.runs_root)
    if export_key not in all_exports:
        raise ResourceNotFoundError(f"Export bundle not found: {export_key!r}")
    b_root, _ = all_exports[export_key]
    resolved = resolve_within_root(b_root, file_path)
    if not resolved.is_file():
        raise ResourceNotFoundError(f"Bundle file not found: {file_path!r}")
    return resolved


def serialize_job(job: JobRecord) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "experiment_id": job.experiment_id,
        "parent_job_id": job.parent_job_id,
        "idempotency_key": job.idempotency_key,
        "kind": job.kind,
        "status": job.status,
        "attempt_number": job.attempt_number,
        "payload": json.loads(job.payload_json),
        "result": None if job.result_json is None else json.loads(job.result_json),
        "error_message": job.error_message,
        "worker_id": job.worker_id,
        "worker_pid": job.worker_pid,
        "created_at_utc": job.created_at_utc.isoformat(),
        "started_at_utc": None if job.started_at_utc is None else job.started_at_utc.isoformat(),
        "ended_at_utc": None if job.ended_at_utc is None else job.ended_at_utc.isoformat(),
        "heartbeat_at_utc": (
            None if job.heartbeat_at_utc is None else job.heartbeat_at_utc.isoformat()
        ),
        "lease_expires_at_utc": (
            None if job.lease_expires_at_utc is None else job.lease_expires_at_utc.isoformat()
        ),
    }


def serialize_protocol_revision(rec: ProtocolRevisionRecord) -> dict[str, Any]:
    return {
        "id": rec.id,
        "protocol_id": rec.protocol_id,
        "revision": rec.revision,
        "status": rec.status,
        "analysis_intent": rec.analysis_intent,
        "protocol_sha256": rec.protocol_sha256,
        "file_path": rec.file_path,
        "frozen_at_utc": None if rec.frozen_at_utc is None else rec.frozen_at_utc.isoformat(),
        "created_at_utc": rec.created_at_utc.isoformat(),
    }


def serialize_audit_event(ev: AuditEventRecord) -> dict[str, Any]:
    return {
        "id": ev.id,
        "created_at_utc": ev.created_at_utc.isoformat(),
        "actor": ev.actor,
        "action": ev.action,
        "resource_type": ev.resource_type,
        "resource_id": ev.resource_id,
        "details": json.loads(ev.details_json),
    }


def create_experiment_record(
    *,
    plan: dict[str, Any],
) -> ExperimentRecord:
    return ExperimentRecord(
        id=f"exp_{uuid.uuid4().hex[:12]}",
        protocol_id=str(plan["protocol_id"]),
        protocol_revision=int(plan["protocol_revision"]),
        protocol_sha256=str(plan["protocol_sha256"]),
        dataset_id=str(plan["dataset_id"]),
        dataset_release=str(plan["dataset_release"]),
        condition_summary_json=json.dumps(plan["conditions"], sort_keys=True),
    )


__all__ = [
    "ProtocolValidationError",
    "ResourceNotFoundError",
    "ServiceValidationError",
    "build_validated_job_payload",
    "create_experiment_record",
    "freeze_protocol_request",
    "get_analysis_detail",
    "get_dataset_plan",
    "get_run_detail",
    "inspect_dataset_graph",
    "list_analyses",
    "list_benchmarks",
    "list_dataset_neurons",
    "list_datasets",
    "list_exports",
    "list_models_and_backends",
    "list_protocols",
    "list_runs",
    "plan_experiment_request",
    "query_dataset_subgraph",
    "resolve_export_file",
    "resolve_run_artifact",
    "serialize_audit_event",
    "serialize_job",
    "serialize_protocol_revision",
    "validate_model_payload",
    "validate_protocol_request",
]
