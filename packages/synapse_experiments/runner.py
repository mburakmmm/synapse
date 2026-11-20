"""Experiment runner: canonical dataset loading, immutable run artifacts, and manifests."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import platform
import subprocess
import uuid
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import polars as pl

from synapse_core import (
    SEED_ALGORITHM,
    Brian2CPUBackend,
    ConstantCurrentStimulus,
    DirectedConnectomeGraph,
    EdgeGainModulation,
    InterventionSpec,
    LIFParameters,
    NeuronSilencing,
    PoissonRateStimulus,
    SeedRecord,
    ShamIntervention,
    SimulationRequest,
    derive_seed,
)
from synapse_data import sha256_file, validate_canonical_dataset
from synapse_experiments.protocol import (
    ProtocolValidationError,
    load_and_validate_protocol,
    validate_run_manifest_schema,
)


def load_graph_from_dataset(
    dataset_dir: Path,
) -> tuple[DirectedConnectomeGraph, dict[str, Any], str]:
    """Validate canonical Parquet dataset and build DirectedConnectomeGraph via vectorized joins."""
    manifest = validate_canonical_dataset(dataset_dir)
    manifest_sha = sha256_file(dataset_dir / "dataset_manifest.json")

    neurons_df = pl.read_parquet(
        dataset_dir / "curated" / "neurons.parquet",
        columns=["source_neuron_id"],
    ).with_row_index("idx", offset=0)
    conns_df = pl.read_parquet(
        dataset_dir / "curated" / "connections.parquet",
        columns=["pre_source_id", "post_source_id", "synapse_count"],
    )
    nts_df = pl.read_parquet(
        dataset_dir / "curated" / "neurotransmitters.parquet",
        columns=["source_neuron_id", "neurotransmitter"],
    )

    neurons_with_nt = neurons_df.join(nts_df, on="source_neuron_id", how="left").sort("idx")
    neuron_ids = neurons_with_nt["source_neuron_id"].to_list()
    nt_list = neurons_with_nt["neurotransmitter"].to_list()

    edges_indexed = conns_df.join(
        neurons_df.rename({"source_neuron_id": "pre_source_id", "idx": "pre_idx"}),
        on="pre_source_id",
        how="inner",
    ).join(
        neurons_df.rename({"source_neuron_id": "post_source_id", "idx": "post_idx"}),
        on="post_source_id",
        how="inner",
    )
    if edges_indexed.height != conns_df.height:
        raise ValueError("Canonical connection foreign key count mismatch during graph indexing")

    graph = DirectedConnectomeGraph.from_arrays(
        dataset_id=str(manifest["dataset_id"]),
        release=str(manifest["release"]),
        specimen_id=str(manifest["specimen_id"] or "unknown_specimen"),
        is_synthetic_fixture=bool(manifest["is_synthetic_fixture"]),
        neuron_ids=neuron_ids,
        pre_indices=edges_indexed["pre_idx"].to_numpy(),
        post_indices=edges_indexed["post_idx"].to_numpy(),
        counts=edges_indexed["synapse_count"].to_numpy(),
        neurotransmitters=nt_list,
        aggregation_policy="sum",
    )
    return graph, manifest, manifest_sha


def collect_source_provenance(repo_root: Path | None = None) -> dict[str, Any]:
    """Capture honest git commit/dirty provenance without fabricating a clean tree."""
    cwd = Path(__file__).resolve().parents[2] if repo_root is None else repo_root
    if not (cwd / ".git").exists():
        return {"git_commit": None, "git_dirty": True, "git_diff_sha256": None}

    head_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    git_commit: str | None = head_proc.stdout.strip() if head_proc.returncode == 0 else None

    status_proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    dirty = bool(status_proc.stdout.strip()) or git_commit is None

    diff_sha256: str | None = None
    if dirty:
        diff_proc = subprocess.run(
            ["git", "diff", "HEAD"] if git_commit is not None else ["git", "diff"],
            cwd=cwd,
            capture_output=True,
            check=False,
        )
        payload = diff_proc.stdout + status_proc.stdout.encode("utf-8")
        diff_sha256 = hashlib.sha256(payload).hexdigest()

    return {
        "git_commit": git_commit,
        "git_dirty": dirty,
        "git_diff_sha256": diff_sha256,
    }


def _collect_environment() -> dict[str, Any]:
    libs: dict[str, str] = {}
    for dist_name in ("numpy", "scipy", "brian2", "polars", "pyarrow", "pydantic", "matplotlib"):
        try:
            libs[dist_name] = pkg_version(dist_name)
        except Exception:  # pragma: no cover - defensive fallback
            libs[dist_name] = "unknown"
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "library_versions": libs,
    }


def parse_lif_parameters(model_cfg: dict[str, Any]) -> LIFParameters:
    """Build validated LIFParameters from protocol model section."""
    raw_params = dict(model_cfg.get("parameters") or {})
    return LIFParameters(
        model_id=str(model_cfg["id"]),
        model_revision=str(model_cfg["revision"]),
        **raw_params,
    )


def parse_interventions(raw_items: Sequence[dict[str, Any]]) -> list[InterventionSpec]:
    """Convert raw protocol intervention dicts into typed immutable intervention specs."""
    parsed: list[InterventionSpec] = []
    for item in raw_items:
        kind = item["kind"]
        if kind == "constant_current":
            parsed.append(
                ConstantCurrentStimulus(
                    target_neuron_ids=tuple(str(x) for x in item["target_neuron_ids"]),
                    current_a=float(item["current_a"]),
                    start_s=float(item.get("start_s", 0.0)),
                    end_s=None if item.get("end_s") is None else float(item["end_s"]),
                )
            )
        elif kind == "poisson_rate":
            parsed.append(
                PoissonRateStimulus(
                    target_neuron_ids=tuple(str(x) for x in item["target_neuron_ids"]),
                    rate_hz=float(item["rate_hz"]),
                    weight_v=float(item["weight_v"]),
                    start_s=float(item.get("start_s", 0.0)),
                    end_s=None if item.get("end_s") is None else float(item["end_s"]),
                    disable_refractory=bool(item.get("disable_refractory", True)),
                )
            )
        elif kind == "edge_gain_modulation":
            parsed.append(
                EdgeGainModulation(
                    target_neuron_ids=tuple(str(x) for x in item["target_neuron_ids"]),
                    scope=item.get("scope", "outgoing"),
                    factor=float(item["factor"]),
                )
            )
        elif kind == "neuron_silencing":
            parsed.append(
                NeuronSilencing(
                    target_neuron_ids=tuple(str(x) for x in item["target_neuron_ids"]),
                    mode=item.get("mode", "outgoing_zero"),
                )
            )
        elif kind == "sham":
            parsed.append(ShamIntervention(description=str(item.get("description", "sham_no_op"))))
        else:
            raise ProtocolValidationError(f"Unsupported intervention kind {kind!r}")
    return parsed


def execute_single_run(
    *,
    runs_dir: Path,
    graph: DirectedConnectomeGraph,
    dataset_manifest: dict[str, Any],
    dataset_manifest_sha256: str,
    protocol: dict[str, Any],
    protocol_sha256: str,
    condition_id: str,
    replicate_id: int,
    interventions: Sequence[InterventionSpec],
    parameters: LIFParameters,
    repo_root: Path | None = None,
    schema_path: Path | None = None,
    graph_sha256: str | None = None,
    source_provenance: dict[str, Any] | None = None,
) -> Path:
    """Execute one simulation run and commit immutable artifacts + validated RunManifest."""
    protocol_id = str(protocol["protocol_id"])
    seeds_cfg = protocol["seeds"]
    master_seed = int(seeds_cfg["master"])
    seed_cond_key = "__paired__" if seeds_cfg["strategy"] == "paired" else condition_id
    derived_brian2 = derive_seed(
        master_seed,
        experiment_id=protocol_id,
        condition_id=seed_cond_key,
        replicate_id=replicate_id,
        stream="brian2",
    )
    seed_record = SeedRecord(
        algorithm=SEED_ALGORITHM,
        master_seed=master_seed,
        derived_seeds={"brian2": derived_brian2},
    )

    stim_cfg = protocol["stimulus_schedule"]
    duration_s = float(stim_cfg["duration_s"])
    mw_cfg = protocol["measurement_window"]
    m_start = float(mw_cfg["start_s"])
    m_end = float(mw_cfg["end_s"])
    res_cfg = protocol["resources"]
    max_wall_s = float(res_cfg["max_wall_seconds"])
    max_out_bytes = int(res_cfg["max_output_bytes"])

    param_sha = parameters.canonical_sha256()
    fingerprint_payload = {
        "protocol_sha256": protocol_sha256,
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "parameter_manifest_sha256": param_sha,
        "condition_id": condition_id,
        "replicate_id": replicate_id,
        "derived_seeds": seed_record.derived_seeds,
    }
    content_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    run_id = f"{protocol_id}_{condition_id}_rep{replicate_id:03d}_{uuid.uuid4().hex[:8]}"
    run_dir = runs_dir / run_id
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "run.log"

    started_at = datetime.now(UTC).isoformat()
    log_lines: list[str] = [
        f"[{started_at}] state=queued run_id={run_id}",
        f"[{started_at}] state=preparing dataset={dataset_manifest['dataset_id']}",
    ]

    spec_payload = {
        "run_id": run_id,
        "content_fingerprint": content_fingerprint,
        "protocol_id": protocol_id,
        "protocol_revision": int(protocol["revision"]),
        "protocol_sha256": protocol_sha256,
        "condition_id": condition_id,
        "replicate_id": replicate_id,
        "dataset_id": dataset_manifest["dataset_id"],
        "dataset_release": dataset_manifest["release"],
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "graph_sha256": graph.graph_sha256() if graph_sha256 is None else graph_sha256,
        "parameters": parameters.model_dump(mode="json"),
        "interventions": [iv.model_dump(mode="json") for iv in interventions],
        "duration_s": duration_s,
        "measurement_window": {"start_s": m_start, "end_s": m_end},
        "seed_info": {
            "algorithm": seed_record.algorithm,
            "master_seed": seed_record.master_seed,
            "derived_seeds": seed_record.derived_seeds,
        },
    }
    spec_path = run_dir / "spec.json"
    spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True), encoding="utf-8")

    backend = Brian2CPUBackend()
    caps = backend.capabilities()
    request = SimulationRequest(
        graph=graph,
        parameters=parameters,
        duration_s=duration_s,
        seed_record=seed_record,
        interventions=interventions,
        max_wall_seconds=max_wall_s,
        measurement_start_s=m_start,
        measurement_end_s=m_end,
    )
    estimate = backend.estimate_resources(request)
    source_prov = (
        collect_source_provenance(repo_root=repo_root)
        if source_provenance is None
        else source_provenance
    )
    env_info = _collect_environment()

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "content_fingerprint": content_fingerprint,
        "status": "running",
        "is_synthetic_fixture": bool(dataset_manifest["is_synthetic_fixture"]),
        "analysis_intent": str(protocol["analysis_intent"]),
        "protocol_id": protocol_id,
        "protocol_revision": int(protocol["revision"]),
        "protocol_sha256": protocol_sha256,
        "experiment_id": protocol_id,
        "condition_id": condition_id,
        "replicate_id": replicate_id,
        "dataset_id": str(dataset_manifest["dataset_id"]),
        "dataset_release": str(dataset_manifest["release"]),
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "model_id": parameters.model_id,
        "model_revision": parameters.model_revision,
        "parameter_manifest_sha256": param_sha,
        "resolved_interventions": [],
        "seed_info": {
            "algorithm": seed_record.algorithm,
            "master_seed": seed_record.master_seed,
            "derived_seeds": seed_record.derived_seeds,
        },
        "source_provenance": source_prov,
        "environment": env_info,
        "simulation_settings": {
            "backend_id": caps.backend_id,
            "solver": parameters.solver,
            "precision": caps.precision,
            "dt_s": parameters.dt_s,
            "duration_s": duration_s,
        },
        "started_at_utc": started_at,
        "ended_at_utc": None,
        "resource_usage": {
            "wall_seconds": None,
            "estimated_memory_bytes": estimate.estimated_memory_bytes,
        },
        "outputs": [],
        "warnings": [],
        "failure_reason": None,
    }

    try:
        log_lines.append(
            f"[{datetime.now(UTC).isoformat()}] state=running backend={caps.backend_id}"
        )
        result = backend.run(request)

        # Write spikes.parquet
        spikes_path = run_dir / "spikes.parquet"
        if len(result.spike_times_s) > 0:
            spikes_df = pl.DataFrame(
                {
                    "run_id": [run_id] * len(result.spike_times_s),
                    "condition_id": [condition_id] * len(result.spike_times_s),
                    "replicate_id": [replicate_id] * len(result.spike_times_s),
                    "source_neuron_id": list(result.spike_neuron_ids),
                    "spike_time_s": result.spike_times_s.tolist(),
                    "is_synthetic_fixture": [bool(dataset_manifest["is_synthetic_fixture"])]
                    * len(result.spike_times_s),
                }
            )
        else:
            spikes_df = pl.DataFrame(
                schema={
                    "run_id": pl.String,
                    "condition_id": pl.String,
                    "replicate_id": pl.Int64,
                    "source_neuron_id": pl.String,
                    "spike_time_s": pl.Float64,
                    "is_synthetic_fixture": pl.Boolean,
                }
            )
        spikes_df.write_parquet(spikes_path)

        # Write metrics.parquet
        spike_counts = [
            round(rate * result.measurement_duration_s) for rate in result.firing_rates_hz
        ]
        metrics_path = run_dir / "metrics.parquet"
        metrics_df = pl.DataFrame(
            {
                "run_id": [run_id] * len(result.neuron_ids),
                "condition_id": [condition_id] * len(result.neuron_ids),
                "replicate_id": [replicate_id] * len(result.neuron_ids),
                "source_neuron_id": list(result.neuron_ids),
                "spike_count": spike_counts,
                "firing_rate_hz": result.firing_rates_hz.tolist(),
                "measurement_duration_s": [result.measurement_duration_s] * len(result.neuron_ids),
                "is_synthetic_fixture": [bool(dataset_manifest["is_synthetic_fixture"])]
                * len(result.neuron_ids),
            }
        )
        metrics_df.write_parquet(metrics_path)

        # Write qc.json
        qc_path = run_dir / "qc.json"
        qc_payload = {
            "passed": True,
            "is_synthetic_fixture": bool(dataset_manifest["is_synthetic_fixture"]),
            "n_neurons": len(result.neuron_ids),
            "total_spikes_in_window": len(result.spike_times_s),
            "all_rates_finite": bool(all(r == r for r in result.firing_rates_hz.tolist())),
            "measurement_duration_s": result.measurement_duration_s,
        }
        qc_path.write_text(json.dumps(qc_payload, indent=2, sort_keys=True), encoding="utf-8")

        log_lines.append(
            f"[{datetime.now(UTC).isoformat()}] state=succeeded "
            f"spikes={len(result.spike_times_s)} wall_s={result.wall_seconds:.4f}"
        )
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

        output_specs = [
            (spec_path, "run_spec"),
            (spikes_path, "spikes_parquet"),
            (metrics_path, "metrics_parquet"),
            (qc_path, "qc_report"),
            (log_path, "execution_log"),
        ]
        total_out_bytes = sum(p.stat().st_size for p, _ in output_specs)
        if total_out_bytes > max_out_bytes:
            raise RuntimeError(
                f"Output artifacts size {total_out_bytes} bytes exceeds "
                f"max_output_bytes={max_out_bytes}"
            )

        outputs_meta = [
            {
                "path": p.relative_to(run_dir).as_posix(),
                "role": role,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
            for p, role in output_specs
        ]
        artifacts_path = run_dir / "artifacts.json"
        artifacts_path.write_text(
            json.dumps({"run_id": run_id, "files": outputs_meta}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        outputs_meta.append(
            {
                "path": "artifacts.json",
                "role": "artifact_index",
                "bytes": artifacts_path.stat().st_size,
                "sha256": sha256_file(artifacts_path),
            }
        )

        manifest["status"] = "succeeded"
        manifest["resolved_interventions"] = [
            rec.model_dump(mode="json") for rec in result.resolved_interventions
        ]
        manifest["ended_at_utc"] = datetime.now(UTC).isoformat()
        manifest["resource_usage"]["wall_seconds"] = result.wall_seconds
        manifest["outputs"] = outputs_meta
        manifest["warnings"] = list(result.warnings)

        validate_run_manifest_schema(manifest, schema_path=schema_path)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

        # Atomic completion marker ONLY after validation succeeds
        complete_tmp = run_dir / "COMPLETE.tmp"
        complete_tmp.write_text(f"{run_id}\n{content_fingerprint}\n", encoding="utf-8")
        complete_tmp.replace(run_dir / "COMPLETE")
        return run_dir

    except Exception as exc:
        ended_at = datetime.now(UTC).isoformat()
        log_lines.append(f"[{ended_at}] state=failed error={exc}")
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        manifest["status"] = "failed"
        manifest["ended_at_utc"] = ended_at
        manifest["failure_reason"] = f"{type(exc).__name__}: {exc}"
        manifest["outputs"] = [
            {
                "path": p.relative_to(run_dir).as_posix(),
                "role": role,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
            for p, role in ((spec_path, "run_spec"), (log_path, "execution_log"))
            if p.is_file()
        ]
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        raise


_WORKER_CTX: tuple[DirectedConnectomeGraph, dict[str, Any], str, str] | None = None


def _init_worker_context(dataset_dir_str: str) -> None:
    global _WORKER_CTX
    graph, manifest, manifest_sha = load_graph_from_dataset(Path(dataset_dir_str))
    _WORKER_CTX = (graph, manifest, manifest_sha, graph.graph_sha256())


def _run_worker_task(task: dict[str, Any]) -> str:
    if _WORKER_CTX is None:
        raise RuntimeError("Worker graph context was not initialized")
    graph, dataset_manifest, dataset_manifest_sha, graph_sha = _WORKER_CTX
    parameters = LIFParameters(**task["parameters_dict"])
    interventions = parse_interventions(task["raw_interventions"])
    run_dir = execute_single_run(
        runs_dir=Path(task["runs_dir"]),
        graph=graph,
        dataset_manifest=dataset_manifest,
        dataset_manifest_sha256=dataset_manifest_sha,
        protocol=task["protocol"],
        protocol_sha256=task["protocol_sha"],
        condition_id=task["condition_id"],
        replicate_id=int(task["replicate_id"]),
        interventions=interventions,
        parameters=parameters,
        graph_sha256=graph_sha,
        source_provenance=task["source_provenance"],
    )
    return str(run_dir)


def run_protocol_experiment(
    protocol_path: Path,
    dataset_dir: Path,
    runs_dir: Path,
    *,
    replicates_override: int | None = None,
    repo_root: Path | None = None,
    workers: int = 1,
) -> list[Path]:
    """Run all conditions and replicates declared in an executable protocol YAML."""
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    protocol, protocol_sha = load_and_validate_protocol(protocol_path, require_executable=True)
    parameters = parse_lif_parameters(protocol["model"])
    source_prov = collect_source_provenance(repo_root=repo_root)

    stim_cfg = protocol["stimulus_schedule"]
    raw_base = list(stim_cfg.get("stimuli", []))

    n_replicates = (
        int(protocol["seeds"]["replicates"])
        if replicates_override is None
        else int(replicates_override)
    )
    if n_replicates < 1:
        raise ProtocolValidationError("replicates must be >= 1")

    if workers == 1:
        graph, dataset_manifest, dataset_manifest_sha = load_graph_from_dataset(dataset_dir)
        graph_sha = graph.graph_sha256()
        base_interventions = parse_interventions(raw_base)
        run_dirs: list[Path] = []
        for cond in protocol["conditions"]:
            condition_id = str(cond["id"])
            cond_interventions = base_interventions + parse_interventions(cond["interventions"])
            for rep in range(n_replicates):
                run_dir = execute_single_run(
                    runs_dir=runs_dir,
                    graph=graph,
                    dataset_manifest=dataset_manifest,
                    dataset_manifest_sha256=dataset_manifest_sha,
                    protocol=protocol,
                    protocol_sha256=protocol_sha,
                    condition_id=condition_id,
                    replicate_id=rep,
                    interventions=cond_interventions,
                    parameters=parameters,
                    repo_root=repo_root,
                    graph_sha256=graph_sha,
                    source_provenance=source_prov,
                )
                run_dirs.append(run_dir)
        return run_dirs

    # Validate dataset upfront before spawning workers
    validate_canonical_dataset(dataset_dir)
    tasks: list[dict[str, Any]] = []
    params_dict = parameters.model_dump(mode="json")
    for cond in protocol["conditions"]:
        condition_id = str(cond["id"])
        raw_interventions = raw_base + list(cond["interventions"])
        for rep in range(n_replicates):
            tasks.append(
                {
                    "runs_dir": str(runs_dir),
                    "protocol": protocol,
                    "protocol_sha": protocol_sha,
                    "condition_id": condition_id,
                    "replicate_id": rep,
                    "raw_interventions": raw_interventions,
                    "parameters_dict": params_dict,
                    "source_provenance": source_prov,
                }
            )

    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_init_worker_context,
        initargs=(str(dataset_dir),),
    ) as pool:
        result_strs = list(pool.map(_run_worker_task, tasks))
    return [Path(s) for s in result_strs]


def plan_protocol_experiment(
    protocol_path: Path,
    dataset_dir: Path,
    *,
    replicates_override: int | None = None,
) -> dict[str, Any]:
    """Dry-run validate protocol/dataset, verify target IDs, and estimate per-run resources."""
    protocol, protocol_sha = load_and_validate_protocol(protocol_path, require_executable=True)
    parameters = parse_lif_parameters(protocol["model"])
    dataset_manifest = validate_canonical_dataset(dataset_dir)
    dataset_manifest_sha = sha256_file(dataset_dir / "dataset_manifest.json")

    neurons_df = pl.read_parquet(
        dataset_dir / "curated" / "neurons.parquet",
        columns=["source_neuron_id"],
    )
    known_ids = set(neurons_df["source_neuron_id"].to_list())
    n_neurons = neurons_df.height
    n_edges = int(
        pl.scan_parquet(dataset_dir / "curated" / "connections.parquet")
        .select(pl.len())
        .collect()
        .item()
    )

    stim_cfg = protocol["stimulus_schedule"]
    duration_s = float(stim_cfg["duration_s"])
    raw_base = list(stim_cfg.get("stimuli", []))
    base_interventions = parse_interventions(raw_base)

    n_replicates = (
        int(protocol["seeds"]["replicates"])
        if replicates_override is None
        else int(replicates_override)
    )
    if n_replicates < 1:
        raise ProtocolValidationError("replicates must be >= 1")

    seeds_cfg = protocol["seeds"]
    master_seed = int(seeds_cfg["master"])
    strategy = str(seeds_cfg["strategy"])
    protocol_id = str(protocol["protocol_id"])

    planned_conditions: list[dict[str, Any]] = []
    planned_runs: list[dict[str, Any]] = []
    for cond in protocol["conditions"]:
        condition_id = str(cond["id"])
        cond_interventions = base_interventions + parse_interventions(cond["interventions"])
        missing_targets: set[str] = set()
        for iv in cond_interventions:
            if not isinstance(iv, ShamIntervention):
                for nid in iv.target_neuron_ids:
                    if nid not in known_ids:
                        missing_targets.add(nid)
        if missing_targets:
            sample = ", ".join(sorted(missing_targets)[:5])
            raise ProtocolValidationError(
                f"Condition {condition_id!r} references neuron ID(s) absent from dataset: {sample}"
            )
        planned_conditions.append(
            {
                "condition_id": condition_id,
                "n_interventions": len(cond_interventions),
                "replicates": n_replicates,
            }
        )
        seed_cond_key = "__paired__" if strategy == "paired" else condition_id
        for rep in range(n_replicates):
            derived_brian2 = derive_seed(
                master_seed,
                experiment_id=protocol_id,
                condition_id=seed_cond_key,
                replicate_id=rep,
                stream="brian2",
            )
            planned_runs.append(
                {
                    "condition_id": condition_id,
                    "replicate_id": rep,
                    "derived_brian2_seed": derived_brian2,
                }
            )

    estimate = Brian2CPUBackend.estimate_from_counts(
        n_neurons=n_neurons,
        n_edges=n_edges,
        duration_s=duration_s,
        dt_s=parameters.dt_s,
        n_voltage_monitored=0,
    )
    res_cfg = protocol["resources"]
    return {
        "status": "planned",
        "protocol_id": protocol_id,
        "protocol_revision": int(protocol["revision"]),
        "protocol_status": str(protocol["status"]),
        "protocol_sha256": protocol_sha,
        "analysis_intent": str(protocol["analysis_intent"]),
        "dataset_id": str(dataset_manifest["dataset_id"]),
        "dataset_release": str(dataset_manifest["release"]),
        "dataset_manifest_sha256": dataset_manifest_sha,
        "is_synthetic_fixture": bool(dataset_manifest["is_synthetic_fixture"]),
        "model_id": parameters.model_id,
        "model_revision": parameters.model_revision,
        "parameter_manifest_sha256": parameters.canonical_sha256(),
        "total_runs": len(planned_runs),
        "conditions": planned_conditions,
        "resource_estimate_per_run": {
            "n_neurons": estimate.n_neurons,
            "n_edges": estimate.n_edges,
            "n_timesteps": estimate.n_timesteps,
            "estimated_memory_bytes": estimate.estimated_memory_bytes,
            "max_wall_seconds": float(res_cfg["max_wall_seconds"]),
            "max_output_bytes": int(res_cfg["max_output_bytes"]),
        },
        "seed_strategy": strategy,
        "master_seed": master_seed,
        "planned_runs": planned_runs,
        "known_limitations": list(dataset_manifest.get("known_limitations", [])),
    }
