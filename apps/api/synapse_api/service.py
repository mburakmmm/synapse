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
    CircadianHomeostaticParameters,
    DirectedConnectomeGraph,
    LIFParameters,
    MBPlasticityParameters,
    TopologyAnalysisParameters,
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
    meta_by_id: dict[str, dict[str, Any]] = {}
    neurons_pq = ds_dir / "curated" / "neurons.parquet"
    if neurons_pq.is_file() and sub.neuron_ids:
        scan = pl.scan_parquet(neurons_pq)
        avail_cols = set(scan.collect_schema().names())
        wanted = [c for c in ("cell_type", "region", "soma_side", "superclass") if c in avail_cols]
        if wanted:
            rows = (
                scan.filter(pl.col("source_neuron_id").is_in(sub.neuron_ids))
                .select(["source_neuron_id", *wanted])
                .collect()
            )
            for row in rows.iter_rows(named=True):
                meta_by_id[str(row["source_neuron_id"])] = row

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
                "cell_type": meta_by_id.get(nid, {}).get("cell_type"),
                "region": meta_by_id.get(nid, {}).get("region"),
                "soma_side": meta_by_id.get(nid, {}).get("soma_side"),
                "superclass": meta_by_id.get(nid, {}).get("superclass"),
            }
            for nid, nt in zip(sub.neuron_ids, sub.neurotransmitters, strict=True)
        ],
        "edges": edges_preview,
        "edges_truncated": len(counts) > 500,
    }


def _serialize_model_entry(params: LIFParameters) -> dict[str, Any]:
    return {
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "model_level": "L1",
        "parameter_manifest_sha256": params.canonical_sha256(),
        "solver": params.solver,
        "dt_s": params.dt_s,
        "dg_unless_refractory": params.dg_unless_refractory,
        "parameter_source": params.parameter_source,
        "parameters": {
            "v_rest_v": params.v_rest_v,
            "v_reset_v": params.v_reset_v,
            "v_threshold_v": params.v_threshold_v,
            "tau_m_s": params.tau_m_s,
            "tau_syn_s": params.tau_syn_s,
            "t_ref_s": params.t_ref_s,
            "delay_s": params.delay_s,
            "w_syn_v": params.w_syn_v,
            "r_m_ohm": params.r_m_ohm,
            "unknown_nt_policy": params.unknown_nt_policy,
        },
    }


def _serialize_plasticity_model_entry(params: MBPlasticityParameters) -> dict[str, Any]:
    return {
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "model_level": params.model_level,
        "parameter_manifest_sha256": params.canonical_sha256(),
        "solver": params.solver,
        "dt_s": params.dt_s,
        "parameter_source": params.parameter_source,
        "parameters": {
            "tau_e_s": params.tau_e_s,
            "tau_d_s": params.tau_d_s,
            "eta_ltd_pam": params.eta_ltd_pam,
            "eta_ltd_ppl1": params.eta_ltd_ppl1,
            "eta_pot_reinst": params.eta_pot_reinst,
            "omission_gain": params.omission_gain,
            "tau_rec_avoid_s": params.tau_rec_avoid_s,
            "tau_rec_appr_s": params.tau_rec_appr_s,
            "w_init": params.w_init,
            "w_min": params.w_min,
            "r_base_hz": params.r_base_hz,
            "g_cross": params.g_cross,
        },
    }


def _serialize_circadian_model_entry(params: CircadianHomeostaticParameters) -> dict[str, Any]:
    return {
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "model_level": params.model_level,
        "parameter_manifest_sha256": params.canonical_sha256(),
        "solver": params.solver,
        "dt_s": params.dt_eval_h * params.seconds_per_hour,
        "parameter_source": params.parameter_source,
        "parameters": {
            "tau_i_h": params.tau_i_h,
            "tau_d_h": params.tau_d_h,
            "v_sP": params.v_sP,
            "v_sT": params.v_sT,
            "v_dT_dark": params.v_dT_dark,
            "v_dT_light": params.v_dT_light,
            "k1": params.k1,
            "k2": params.k2,
            "k3": params.k3,
            "k4": params.k4,
            "u_mean": params.u_mean,
            "l_mean": params.l_mean,
            "a_c": params.a_c,
        },
    }


def _serialize_topology_model_entry(params: TopologyAnalysisParameters) -> dict[str, Any]:
    return {
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "model_level": params.model_level,
        "parameter_manifest_sha256": params.canonical_sha256(),
        "solver": "csgraph_dijkstra",
        "dt_s": 0.0,
        "parameter_source": params.parameter_source,
        "parameters": {
            "min_synapse_threshold": params.min_synapse_threshold,
            "excitatory_only_pathway": params.excitatory_only_pathway,
            "distance_weighting": params.distance_weighting,
        },
    }


def list_models_and_backends() -> dict[str, Any]:
    topology_l0 = TopologyAnalysisParameters()
    default_lif = LIFParameters()
    shiu_lif = LIFParameters.shiu2024_reference()
    plasticity_l2 = MBPlasticityParameters()
    circadian_l3 = CircadianHomeostaticParameters()
    cpu_caps = Brian2CPUBackend().capabilities()
    return {
        "models": [
            _serialize_topology_model_entry(topology_l0),
            _serialize_model_entry(default_lif),
            _serialize_model_entry(shiu_lif),
            _serialize_plasticity_model_entry(plasticity_l2),
            _serialize_circadian_model_entry(circadian_l3),
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


def get_protocol_content(settings: Settings, protocol_path: str) -> dict[str, Any]:
    """Read YAML text and parsed metadata for an allowlisted protocol file."""
    resolved = resolve_within_root(settings.protocols_root, protocol_path)
    if not resolved.is_file():
        raise ResourceNotFoundError(f"Protocol file not found: {protocol_path!r}")
    yaml_text = resolved.read_text(encoding="utf-8")
    rel = resolved.relative_to(settings.protocols_root).as_posix()
    payload: dict[str, Any] = {
        "relative_path": rel,
        "yaml_text": yaml_text,
        "size_bytes": len(yaml_text.encode("utf-8")),
    }
    try:
        doc, sha = load_and_validate_protocol(resolved, require_executable=False)
        payload.update(
            {
                "protocol_id": doc["protocol_id"],
                "revision": doc["revision"],
                "status": doc["status"],
                "analysis_intent": doc["analysis_intent"],
                "protocol_sha256": sha,
                "question": doc.get("question"),
                "hypothesis": doc.get("hypothesis"),
                "conditions_count": len(doc.get("conditions", [])),
                "validation_error": None,
            }
        )
    except Exception as exc:
        payload["validation_error"] = str(exc)
    return payload


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


_JSON_STAT_CACHE: dict[Path, tuple[int, int, dict[str, Any]]] = {}
_PRUNE_COMMON_DIRS = {"_worker_tmp", "logs", "figures", "tables", "dataset", "__pycache__"}


def _read_cached_json(path: Path) -> dict[str, Any] | None:
    try:
        st = path.stat()
        cached = _JSON_STAT_CACHE.get(path)
        if cached is not None and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            if len(_JSON_STAT_CACHE) > 2048:
                _JSON_STAT_CACHE.clear()
            _JSON_STAT_CACHE[path] = (st.st_mtime_ns, st.st_size, parsed)
            return parsed
    except Exception:
        return None
    return None


def _iter_run_manifests(runs_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not runs_root.is_dir():
        return found
    skip_dirs = _PRUNE_COMMON_DIRS | {"provenance", "evaluation"}
    for root_str, dirnames, filenames in os.walk(runs_root):
        if "manifest.json" in filenames:
            m_path = Path(root_str) / "manifest.json"
            data = _read_cached_json(m_path)
            if data is not None:
                run_id = str(data.get("run_id", "")).strip()
                if run_id and "protocol_id" in data:
                    found[run_id] = (Path(root_str), data)
            dirnames.clear()
            continue
        dirnames[:] = sorted(
            d for d in dirnames if d not in skip_dirs and not d.startswith(("analysis_", "bundle_"))
        )
    return found


def list_runs(
    settings: Settings,
    *,
    limit: int = 50,
    offset: int = 0,
    condition_id: str | None = None,
    status: str | None = None,
    protocol_id: str | None = None,
) -> dict[str, Any]:
    all_runs = _iter_run_manifests(settings.runs_root)
    rows: list[dict[str, Any]] = []
    for run_id, (r_dir, m) in all_runs.items():
        if condition_id and m.get("condition_id") != condition_id:
            continue
        if status and m.get("status") != status:
            continue
        if protocol_id and m.get("protocol_id") != protocol_id:
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


def _read_json_if_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def list_research_studies(settings: Settings) -> dict[str, Any]:
    """Summarize real on-disk benchmark and module study outputs strictly as read-only RUO data."""
    benchmarks = list_benchmarks(settings)["benchmarks"]
    shiu_available = len(benchmarks) > 0
    shiu_reproduced = any(bool(item["report"].get("overall_passed")) for item in benchmarks)

    met_conf_dir = settings.runs_root / "phase4_met001_confirmatory"
    met_conf_list: list[dict[str, Any]] = []
    if met_conf_dir.is_dir():
        for analysis_dir in sorted(met_conf_dir.glob("analysis_*")):
            manifest = _read_json_if_file(analysis_dir / "analysis_manifest.json")
            if manifest is None:
                continue
            met_conf_list.append(
                {
                    "analysis_key": analysis_dir.name,
                    "target_neuron_id": str(manifest.get("target_neuron_id", "")),
                    "baseline_condition": manifest.get("baseline_condition"),
                    "treatment_condition": manifest.get("treatment_condition"),
                    "condition_summaries": manifest.get("condition_summaries", {}),
                    "paired_metrics": manifest.get("paired_metrics", {}),
                    "failed_run_count": manifest.get("failed_run_count", 0),
                    "provenance": manifest.get("provenance", {}),
                }
            )

    met_robust_dir = settings.runs_root / "phase4_met001_robustness"
    met_robust: dict[str, Any] = {}
    if met_robust_dir.is_dir():
        for arm_name in ("canonical_lif", "wsyn_low", "wsyn_high"):
            arm_manifest = _read_json_if_file(
                met_robust_dir / arm_name / "analysis_mn9r" / "analysis_manifest.json"
            )
            if arm_manifest is not None:
                met_robust[arm_name] = {
                    "target_neuron_id": str(arm_manifest.get("target_neuron_id", "")),
                    "baseline_condition": arm_manifest.get("baseline_condition"),
                    "treatment_condition": arm_manifest.get("treatment_condition"),
                    "condition_summaries": arm_manifest.get("condition_summaries", {}),
                    "paired_metrics": arm_manifest.get("paired_metrics", {}),
                    "provenance": arm_manifest.get("provenance", {}),
                }

    pain_conf_dir = settings.runs_root / "phase5_pain001_confirmatory"
    pain_conf = _read_json_if_file(pain_conf_dir / "confirmatory_summary.json")
    pain_win_raw = _read_json_if_file(pain_conf_dir / "windowed_summary.json")
    pain_win_trimmed: dict[str, Any] | None = None
    if pain_win_raw is not None:
        pain_win_trimmed = {
            "windows": pain_win_raw.get("windows", {}),
            "neuron_ids": [str(nid) for nid in pain_win_raw.get("neuron_ids", [])],
            "succeeded_run_count": pain_win_raw.get("succeeded_run_count", 0),
            "failed_run_count": pain_win_raw.get("failed_run_count", 0),
            "per_neuron_condition_summaries": pain_win_raw.get(
                "per_neuron_condition_summaries", {}
            ),
        }
    pain_rob = _read_json_if_file(
        settings.runs_root / "phase5_pain001_robustness" / "robustness_summary.json"
    )

    sleep_l3_dir = settings.runs_root / "phase5b_sleep001_l3_oscillator"
    sleep_l3_gate = _read_json_if_file(sleep_l3_dir / "l3_verification_gate.json")
    sleep_l3_shift_raw = _read_json_if_file(sleep_l3_dir / "l3_shift_work_summary.json")
    sleep_l3_shift: dict[str, Any] | None = None
    if sleep_l3_shift_raw is not None:
        trimmed_arms: dict[str, Any] = {}
        for arm_id, arm in (sleep_l3_shift_raw.get("arms") or {}).items():
            if not isinstance(arm, dict):
                continue
            trimmed_arms[str(arm_id)] = {
                "arm_id": arm.get("arm_id"),
                "duration_h": arm.get("duration_h"),
                "s_peak_overall": arm.get("s_peak_overall"),
                "s_mean_post_onset": arm.get("s_mean_post_onset"),
                "modeled_rest_fraction_post_onset": arm.get("modeled_rest_fraction_post_onset"),
                "max_abs_phase_error_h": arm.get("max_abs_phase_error_h"),
                "days_to_reentrain": arm.get("days_to_reentrain"),
                "post_onset_phase_errors": arm.get("post_onset_phase_errors", []),
            }
        sleep_l3_shift = {
            "model_id": sleep_l3_shift_raw.get("model_id"),
            "model_level": sleep_l3_shift_raw.get("model_level"),
            "parameter_manifest_sha256": sleep_l3_shift_raw.get("parameter_manifest_sha256"),
            "timescale_coupling_note": sleep_l3_shift_raw.get("timescale_coupling_note"),
            "gate_overall_passed": sleep_l3_shift_raw.get("gate_overall_passed"),
            "arms": trimmed_arms,
            "l3_to_l1_coupling_snapshots": sleep_l3_shift_raw.get(
                "l3_to_l1_coupling_snapshots", []
            ),
        }

    sleep_pilot_dir = settings.runs_root / "phase5b_sleep001_exploratory_pilot"
    sleep_pilot = _read_json_if_file(sleep_pilot_dir / "pilot_summary.json")
    sleep_win_raw = _read_json_if_file(sleep_pilot_dir / "windowed_summary.json")
    sleep_win_trimmed: dict[str, Any] | None = None
    if sleep_win_raw is not None:
        sleep_win_trimmed = {
            "windows": sleep_win_raw.get("windows", {}),
            "neuron_ids": [str(nid) for nid in sleep_win_raw.get("neuron_ids", [])],
            "succeeded_run_count": sleep_win_raw.get("succeeded_run_count", 0),
            "failed_run_count": sleep_win_raw.get("failed_run_count", 0),
        }

    add_l2_dir = settings.runs_root / "phase5b_add001_l2_plasticity"
    add_l2_gate = _read_json_if_file(add_l2_dir / "l2_verification_gate.json")
    add_l2_paradigm_raw = _read_json_if_file(add_l2_dir / "l2_paradigm_summary.json")
    add_l2_paradigm: dict[str, Any] | None = None
    if add_l2_paradigm_raw is not None:
        add_l2_paradigm = {
            "model_id": add_l2_paradigm_raw.get("model_id"),
            "model_level": add_l2_paradigm_raw.get("model_level"),
            "parameter_manifest_sha256": add_l2_paradigm_raw.get("parameter_manifest_sha256"),
            "timescale_coupling_note": add_l2_paradigm_raw.get("timescale_coupling_note"),
            "gate_overall_passed": add_l2_paradigm_raw.get("gate_overall_passed"),
            "arms": add_l2_paradigm_raw.get("arms", {}),
            "l2_to_l1_weight_snapshots": add_l2_paradigm_raw.get("l2_to_l1_weight_snapshots", []),
        }

    add_pilot_dir = settings.runs_root / "phase5b_add001_exploratory_pilot"
    add_pilot = _read_json_if_file(add_pilot_dir / "pilot_summary.json")
    add_win_raw = _read_json_if_file(add_pilot_dir / "windowed_summary.json")
    add_win_trimmed: dict[str, Any] | None = None
    if add_win_raw is not None:
        add_win_trimmed = {
            "windows": add_win_raw.get("windows", {}),
            "neuron_ids": [str(nid) for nid in add_win_raw.get("neuron_ids", [])],
            "succeeded_run_count": add_win_raw.get("succeeded_run_count", 0),
            "failed_run_count": add_win_raw.get("failed_run_count", 0),
        }

    neuro_l0_dir = settings.runs_root / "phase5c_neuro001_l0_topology"
    neuro_l0_gate = _read_json_if_file(neuro_l0_dir / "l0_verification_gate.json")
    neuro_l0_summary = _read_json_if_file(neuro_l0_dir / "l0_ablation_summary.json")
    neuro_malecns_audit = _read_json_if_file(neuro_l0_dir / "malecns_l0_structural_audit.json")
    neuro_pilot_dir = settings.runs_root / "phase5c_neuro001_exploratory_pilot"
    neuro_pilot = _read_json_if_file(neuro_pilot_dir / "pilot_summary.json")

    met_available = len(met_conf_list) > 0
    pain_available = pain_conf is not None
    sleep_available = sleep_l3_gate is not None or sleep_pilot is not None
    if sleep_l3_gate is not None and sleep_pilot is not None:
        sleep_phase = "l3_verified_and_l1_pilot_complete"
    elif sleep_l3_gate is not None:
        sleep_phase = "l3_verified"
    else:
        sleep_phase = "planned"

    addiction_available = add_l2_gate is not None or add_pilot is not None
    if add_l2_gate is not None and add_pilot is not None:
        addiction_phase = "l2_verified_and_l1_pilot_complete"
    elif add_l2_gate is not None:
        addiction_phase = "l2_verified"
    else:
        addiction_phase = "planned"

    neuro_available = neuro_l0_gate is not None or neuro_pilot is not None
    if neuro_l0_gate is not None and neuro_pilot is not None:
        neuro_phase = "l0_verified_and_l1_pilot_complete"
    elif neuro_l0_gate is not None:
        neuro_phase = "l0_verified"
    else:
        neuro_phase = "planned"

    modules = [
        {
            "module_id": "shiu2024_benchmark",
            "phase": "phase2",
            "ui_state": "reproduced" if shiu_reproduced else "experimental",
            "simulation_phase": "computationally_reproduced" if shiu_reproduced else "planned",
            "dataset_id": "flywire_fafb_v630",
            "protocol_id": "P2-BENCH-SHIU2024",
            "available_on_disk": shiu_available,
        },
        {
            "module_id": "metabolic",
            "phase": "phase4",
            "ui_state": "experimental",
            "simulation_phase": (
                "confirmatory_simulation_complete" if met_available else "planned"
            ),
            "dataset_id": "flywire_fafb_v630",
            "protocol_id": "P4-MET-001",
            "available_on_disk": met_available,
        },
        {
            "module_id": "pain",
            "phase": "phase5a",
            "ui_state": "experimental",
            "simulation_phase": (
                "confirmatory_simulation_complete" if pain_available else "planned"
            ),
            "dataset_id": "malecns_v1_0",
            "protocol_id": "P5-PAIN-001",
            "available_on_disk": pain_available,
        },
        {
            "module_id": "sleep",
            "phase": "phase5b",
            "ui_state": "experimental" if sleep_available else "planned",
            "simulation_phase": sleep_phase,
            "dataset_id": "malecns_v1_0" if sleep_available else None,
            "protocol_id": "P5-SLEEP-001-PILOT" if sleep_pilot is not None else None,
            "available_on_disk": sleep_available,
        },
        {
            "module_id": "addiction",
            "phase": "phase5b",
            "ui_state": "experimental" if addiction_available else "planned",
            "simulation_phase": addiction_phase,
            "dataset_id": "malecns_v1_0" if addiction_available else None,
            "protocol_id": "P5-ADD-001-PILOT" if add_pilot is not None else None,
            "available_on_disk": addiction_available,
        },
        {
            "module_id": "neuro",
            "phase": "phase5c",
            "ui_state": "experimental" if neuro_available else "planned",
            "simulation_phase": neuro_phase,
            "dataset_id": "flywire_fafb_v630" if neuro_available else None,
            "protocol_id": "P5-NEURO-001-PILOT" if neuro_pilot is not None else None,
            "available_on_disk": neuro_available,
        },
        {
            "module_id": "pharma",
            "phase": "phase5c",
            "ui_state": "planned",
            "simulation_phase": "planned",
            "dataset_id": None,
            "protocol_id": None,
            "available_on_disk": False,
        },
        {
            "module_id": "stress",
            "phase": "phase5c",
            "ui_state": "planned",
            "simulation_phase": "planned",
            "dataset_id": None,
            "protocol_id": None,
            "available_on_disk": False,
        },
    ]

    return {
        "modules": modules,
        "metabolic": {
            "confirmatory": met_conf_list,
            "robustness": met_robust,
        },
        "pain": {
            "confirmatory": pain_conf,
            "windowed": pain_win_trimmed,
            "robustness": pain_rob,
        },
        "sleep": {
            "l3_gate": sleep_l3_gate,
            "l3_shift_work": sleep_l3_shift,
            "pilot": sleep_pilot,
            "windowed": sleep_win_trimmed,
        },
        "addiction": {
            "l2_gate": add_l2_gate,
            "l2_paradigm": add_l2_paradigm,
            "pilot": add_pilot,
            "windowed": add_win_trimmed,
        },
        "neuro": {
            "l0_gate": neuro_l0_gate,
            "l0_summary": neuro_l0_summary,
            "malecns_l0_audit": neuro_malecns_audit,
            "pilot": neuro_pilot,
        },
    }


def list_benchmarks(settings: Settings) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    if settings.runs_root.is_dir():
        skip_dirs = _PRUNE_COMMON_DIRS | {"runs", "provenance"}
        for root_str, dirnames, filenames in os.walk(settings.runs_root):
            if "benchmark_report.json" in filenames:
                b_path = Path(root_str) / "benchmark_report.json"
                data = _read_cached_json(b_path)
                if data is not None:
                    reports.append(
                        {
                            "relative_path": b_path.relative_to(settings.runs_root).as_posix(),
                            "report": data,
                        }
                    )
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in skip_dirs and not d.startswith(("analysis_", "bundle_"))
            )
    reports.sort(key=lambda item: str(item["relative_path"]))
    return {"benchmarks": reports}


def _iter_analyses(runs_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not runs_root.is_dir():
        return found
    skip_dirs = _PRUNE_COMMON_DIRS | {"runs", "provenance", "evaluation"}
    for root_str, dirnames, filenames in os.walk(runs_root):
        if "analysis_manifest.json" in filenames:
            a_dir = Path(root_str)
            data = _read_cached_json(a_dir / "analysis_manifest.json")
            if data is not None:
                rel = a_dir.relative_to(runs_root).as_posix()
                key = rel.replace("/", "__")
                found[key] = (a_dir, data)
            dirnames.clear()
            continue
        dirnames[:] = sorted(
            d for d in dirnames if d not in skip_dirs and not d.startswith("bundle_")
        )
    return dict(sorted(found.items()))


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
    skip_dirs = _PRUNE_COMMON_DIRS | {"runs", "evaluation"}
    for root_str, dirnames, filenames in os.walk(runs_root):
        cur_dir = Path(root_str)
        if cur_dir.name == "provenance" and "bundle_manifest.json" in filenames:
            bundle_root = cur_dir.parent
            data = _read_cached_json(cur_dir / "bundle_manifest.json")
            if data is not None:
                rel = bundle_root.relative_to(runs_root).as_posix()
                key = rel.replace("/", "__")
                found[key] = (bundle_root, data)
            dirnames.clear()
            continue
        dirnames[:] = sorted(
            d for d in dirnames if d not in skip_dirs and not d.startswith("analysis_")
        )
    return dict(sorted(found.items()))


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
    "get_protocol_content",
    "get_run_detail",
    "inspect_dataset_graph",
    "list_analyses",
    "list_benchmarks",
    "list_dataset_neurons",
    "list_datasets",
    "list_exports",
    "list_models_and_backends",
    "list_protocols",
    "list_research_studies",
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
