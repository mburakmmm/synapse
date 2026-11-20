"""CLI entrypoints calling SYNAPSE scientific packages directly (offline-safe)."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from collections.abc import Sequence
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import yaml

from synapse_analysis import run_paired_analysis
from synapse_core import (
    Brian2CPUBackend,
    LIFParameters,
    extract_bounded_subgraph,
    validate_model_spec,
)
from synapse_data import (
    build_default_registry,
    ingest_synthetic_fixture,
    validate_canonical_dataset,
)
from synapse_experiments import (
    cancel_local_job,
    evaluate_shiu2024_benchmark,
    freeze_protocol,
    get_local_job_status,
    load_and_validate_protocol,
    load_graph_from_dataset,
    plan_protocol_experiment,
    run_protocol_experiment,
    start_local_job,
)
from synapse_publication import export_evidence_bundle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _emit(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _cmd_doctor(args: argparse.Namespace) -> int:
    backend = Brian2CPUBackend()
    caps = backend.capabilities()
    libs: dict[str, str] = {}
    for pkg in ("numpy", "scipy", "brian2", "polars", "pyarrow", "pydantic", "matplotlib"):
        try:
            libs[pkg] = pkg_version(pkg)
        except Exception:
            libs[pkg] = "missing"
    graphify_bin = shutil.which("graphify")
    payload = {
        "status": "ok",
        "ruo_notice": "Research Use Only (RUO) - not for clinical or diagnostic use",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "default_backend": caps.backend_id,
        "backend_device": caps.device,
        "reproducibility_class": caps.reproducibility_class,
        "libraries": libs,
        "graphify_cli_available": graphify_bin is not None,
        "graphify_cli_path": graphify_bin,
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_dataset_list(args: argparse.Namespace) -> int:
    reg = build_default_registry()
    items = [reg.get(did).discover() for did in reg.list_dataset_ids()]
    payload = {"datasets": items}
    _emit(payload, as_json=args.json)
    return 0


def _cmd_dataset_plan(args: argparse.Namespace) -> int:
    reg = build_default_registry()
    adapter = reg.get(args.dataset_id)
    plan = adapter.plan().to_dict()
    _emit(plan, as_json=args.json)
    return 0


def _cmd_dataset_ingest_fixture(args: argparse.Namespace) -> int:
    raw_dir = (
        _repo_root() / "tests" / "fixtures" / "synthetic_microcircuit_v1"
        if args.raw_dir is None
        else Path(args.raw_dir)
    )
    out_dir = Path(args.out)
    manifest_path = ingest_synthetic_fixture(raw_dir, out_dir)
    payload = {
        "status": "succeeded",
        "manifest_path": str(manifest_path),
        "is_synthetic_fixture": True,
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_dataset_fetch(args: argparse.Namespace) -> int:
    reg = build_default_registry()
    adapter = reg.get(args.dataset_id)
    raw_dir = Path(args.raw_dir)
    curated_dir = Path(args.curated_dir)
    adapter.fetch(raw_dir, approved=bool(args.approve))
    if not adapter.verify(raw_dir):
        raise ValueError(f"Raw artifact verification failed in {raw_dir}")
    manifest_path = adapter.normalize(raw_dir, curated_dir)
    manifest = adapter.validate(curated_dir)
    payload = {
        "status": "succeeded",
        "dataset_id": manifest["dataset_id"],
        "release": manifest["release"],
        "is_synthetic_fixture": manifest["is_synthetic_fixture"],
        "manifest_path": str(manifest_path),
        "quality_report": manifest["quality_report"],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_dataset_verify(args: argparse.Namespace) -> int:
    manifest = validate_canonical_dataset(Path(args.dataset_dir))
    payload = {
        "status": "valid",
        "dataset_id": manifest["dataset_id"],
        "release": manifest["release"],
        "is_synthetic_fixture": manifest["is_synthetic_fixture"],
        "quality_report": manifest["quality_report"],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_graph_inspect(args: argparse.Namespace) -> int:
    graph, manifest, manifest_sha = load_graph_from_dataset(Path(args.dataset_dir))
    payload = {
        "dataset_id": graph.dataset_id,
        "release": graph.release,
        "specimen_id": graph.specimen_id,
        "is_synthetic_fixture": graph.is_synthetic_fixture,
        "dataset_manifest_sha256": manifest_sha,
        "graph_sha256": graph.graph_sha256(),
        "n_neurons": graph.n_neurons,
        "n_edges": graph.n_edges,
        "total_synapses": graph.total_synapses,
        "orientation": "row=post_idx(target), col=pre_idx(source)",
        "known_limitations": manifest["known_limitations"],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_graph_subgraph(args: argparse.Namespace) -> int:
    graph, _, _ = load_graph_from_dataset(Path(args.dataset_dir))
    seeds = [s.strip() for s in str(args.seeds).split(",") if s.strip()]
    _, meta = extract_bounded_subgraph(
        graph,
        seed_neuron_ids=seeds,
        hop_limit=args.hops,
        direction=args.direction,
        min_synapse_threshold=args.min_synapses,
        max_nodes=args.max_nodes,
    )
    payload = meta.model_dump(mode="json")
    if args.out is not None:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _emit(payload, as_json=args.json)
    return 0


def _cmd_model_list(args: argparse.Namespace) -> int:
    default_lif = LIFParameters()
    shiu_lif = LIFParameters.shiu2024_reference()
    backend = Brian2CPUBackend()
    caps = backend.capabilities()
    payload = {
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
                "backend_id": caps.backend_id,
                "device": caps.device,
                "precision": caps.precision,
                "supported_solvers": list(caps.supported_solvers),
            }
        ],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_model_validate(args: argparse.Namespace) -> int:
    spec_path = Path(args.path)
    if not spec_path.is_file():
        raise FileNotFoundError(f"Model spec file not found: {spec_path}")
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("model"), dict):
        raw = raw["model"]
    if not isinstance(raw, dict):
        raise ValueError("Model spec file must contain a mapping")
    payload = validate_model_spec(raw)
    _emit(payload, as_json=args.json)
    return 0


def _cmd_benchmark_reproduce(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    runs_dir = out_dir / "runs"
    eval_dir = out_dir / "evaluation"
    run_dirs = run_protocol_experiment(
        protocol_path=Path(args.protocol),
        dataset_dir=Path(args.dataset_dir),
        runs_dir=runs_dir,
        replicates_override=args.replicates,
        repo_root=_repo_root(),
        workers=args.workers,
    )
    report_path = evaluate_shiu2024_benchmark(
        runs_dir=runs_dir,
        reference_targets_path=Path(args.reference_targets),
        out_dir=eval_dir,
        expected_replicates_override=args.replicates,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    payload = {
        "status": "passed" if report["overall_passed"] else "failed",
        "overall_passed": report["overall_passed"],
        "n_runs_completed": len(run_dirs),
        "failed_run_count": report["failed_run_count"],
        "report_path": str(report_path),
        "target_comparisons": report["target_comparisons"],
        "contrast_comparisons": report["contrast_comparisons"],
    }
    _emit(payload, as_json=args.json)
    return 0 if report["overall_passed"] else 3


def _cmd_protocol_validate(args: argparse.Namespace) -> int:
    protocol, sha = load_and_validate_protocol(
        Path(args.path),
        require_executable=not args.allow_unresolved,
    )
    payload = {
        "status": "valid",
        "protocol_id": protocol["protocol_id"],
        "revision": protocol["revision"],
        "protocol_status": protocol["status"],
        "analysis_intent": protocol["analysis_intent"],
        "executable": not args.allow_unresolved,
        "protocol_sha256": sha,
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_protocol_freeze(args: argparse.Namespace) -> int:
    out_path = None if args.out is None else Path(args.out)
    frozen_path, doc, frozen_sha = freeze_protocol(
        Path(args.path),
        out_path=out_path,
        confirmed=bool(args.confirm_freeze),
    )
    payload = {
        "status": "frozen",
        "protocol_id": doc["protocol_id"],
        "revision": doc["revision"],
        "frozen_at_utc": doc["frozen_at_utc"],
        "frozen_path": str(frozen_path),
        "protocol_sha256": frozen_sha,
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_run_plan(args: argparse.Namespace) -> int:
    payload = plan_protocol_experiment(
        Path(args.protocol),
        Path(args.dataset_dir),
        replicates_override=args.replicates,
    )
    _emit(payload, as_json=args.json)
    return 0


def _cmd_run_start(args: argparse.Namespace) -> int:
    payload = start_local_job(
        Path(args.protocol),
        Path(args.dataset_dir),
        Path(args.work_dir),
        replicates_override=args.replicates,
        workers=args.workers,
        detach=bool(args.detach),
    )
    _emit(payload, as_json=args.json)
    return 0


def _cmd_run_status(args: argparse.Namespace) -> int:
    payload = get_local_job_status(Path(args.work_dir))
    _emit(payload, as_json=args.json)
    return 0


def _cmd_run_cancel(args: argparse.Namespace) -> int:
    payload = cancel_local_job(Path(args.work_dir))
    _emit(payload, as_json=args.json)
    return 0


def _cmd_run_synthetic_demo(args: argparse.Namespace) -> int:
    work_dir = Path(args.work_dir)
    dataset_dir = work_dir / "dataset"
    runs_dir = work_dir / "runs"
    analysis_dir = work_dir / "analysis"
    bundle_dir = work_dir / "bundle"

    raw_dir = _repo_root() / "tests" / "fixtures" / "synthetic_microcircuit_v1"
    protocol_path = _repo_root() / "research" / "protocols" / "P0-SYNTH-001.yaml"

    manifest_path = ingest_synthetic_fixture(raw_dir, dataset_dir)
    run_dirs = run_protocol_experiment(
        protocol_path=protocol_path,
        dataset_dir=dataset_dir,
        runs_dir=runs_dir,
        replicates_override=args.seeds,
        repo_root=_repo_root(),
    )
    analysis_manifest_path = run_paired_analysis(
        runs_dir=runs_dir,
        out_dir=analysis_dir,
        baseline_condition="baseline",
        treatment_condition="inhibitory_silencing",
        target_neuron_id="9007199254740996",
    )
    bundle_manifest_path = export_evidence_bundle(analysis_dir=analysis_dir, out_dir=bundle_dir)
    analysis_data = json.loads(analysis_manifest_path.read_text(encoding="utf-8"))

    payload = {
        "status": "succeeded",
        "is_synthetic_fixture": True,
        "notice": "Synthetic engineering demonstration only; zero biological claims.",
        "dataset_manifest": str(manifest_path),
        "n_runs_completed": len(run_dirs),
        "analysis_manifest": str(analysis_manifest_path),
        "bundle_manifest": str(bundle_manifest_path),
        "paired_metrics": analysis_data["paired_metrics"],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_analysis_run(args: argparse.Namespace) -> int:
    manifest_path = run_paired_analysis(
        runs_dir=Path(args.runs_dir),
        out_dir=Path(args.out),
        baseline_condition=args.baseline,
        treatment_condition=args.treatment,
        target_neuron_id=args.neuron_id,
    )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = {
        "status": "succeeded",
        "analysis_manifest": str(manifest_path),
        "failed_run_count": data["failed_run_count"],
        "paired_metrics": data["paired_metrics"],
    }
    _emit(payload, as_json=args.json)
    return 0


def _cmd_export_bundle(args: argparse.Namespace) -> int:
    bundle_manifest = export_evidence_bundle(
        analysis_dir=Path(args.analysis_dir),
        out_dir=Path(args.out),
    )
    payload = {"status": "succeeded", "bundle_manifest": str(bundle_manifest)}
    _emit(payload, as_json=args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synapse",
        description="SYNAPSE: Reproducible computational neuroscience research CLI (RUO)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Inspect environment, backend, and Graphify status")
    p_doc.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p_doc.set_defaults(func=_cmd_doctor)

    # dataset
    p_ds = sub.add_parser("dataset", help="Inspect registered datasets, plans, and fixtures")
    ds_sub = p_ds.add_subparsers(dest="dataset_cmd", required=True)

    p_ds_list = ds_sub.add_parser("list", help="List registered datasets")
    p_ds_list.add_argument("--json", action="store_true")
    p_ds_list.set_defaults(func=_cmd_dataset_list)

    p_ds_plan = ds_sub.add_parser("plan", help="Show explicit fetch plan (offline, no download)")
    p_ds_plan.add_argument("dataset_id")
    p_ds_plan.add_argument("--json", action="store_true")
    p_ds_plan.set_defaults(func=_cmd_dataset_plan)

    p_ds_ing = ds_sub.add_parser("ingest-fixture", help="Ingest local synthetic fixture")
    p_ds_ing.add_argument("--out", required=True)
    p_ds_ing.add_argument("--raw-dir", default=None)
    p_ds_ing.add_argument("--json", action="store_true")
    p_ds_ing.set_defaults(func=_cmd_dataset_ingest_fixture)

    p_ds_fetch = ds_sub.add_parser(
        "fetch", help="Fetch, verify, and normalize dataset (requires --approve)"
    )
    p_ds_fetch.add_argument("dataset_id")
    p_ds_fetch.add_argument("--raw-dir", required=True)
    p_ds_fetch.add_argument("--curated-dir", required=True)
    p_ds_fetch.add_argument(
        "--approve",
        action="store_true",
        help="Explicit authorization to download external biological datasets",
    )
    p_ds_fetch.add_argument("--json", action="store_true")
    p_ds_fetch.set_defaults(func=_cmd_dataset_fetch)

    p_ds_ver = ds_sub.add_parser("verify", help="Verify canonical dataset checksums and data gates")
    p_ds_ver.add_argument("dataset_dir")
    p_ds_ver.add_argument("--json", action="store_true")
    p_ds_ver.set_defaults(func=_cmd_dataset_verify)

    # graph
    p_gr = sub.add_parser("graph", help="Inspect validated canonical graph")
    gr_sub = p_gr.add_subparsers(dest="graph_cmd", required=True)
    p_gr_ins = gr_sub.add_parser("inspect", help="Inspect graph invariants and checksum")
    p_gr_ins.add_argument("--dataset-dir", required=True)
    p_gr_ins.add_argument("--json", action="store_true")
    p_gr_ins.set_defaults(func=_cmd_graph_inspect)

    p_gr_sub = gr_sub.add_parser(
        "subgraph", help="Extract bounded induced subgraph with boundary stats"
    )
    p_gr_sub.add_argument("--dataset-dir", required=True)
    p_gr_sub.add_argument("--seeds", required=True, help="Comma-separated neuron IDs")
    p_gr_sub.add_argument("--hops", type=int, default=1)
    p_gr_sub.add_argument(
        "--direction", choices=["outgoing", "incoming", "both"], default="outgoing"
    )
    p_gr_sub.add_argument("--min-synapses", type=int, default=1)
    p_gr_sub.add_argument("--max-nodes", type=int, default=5000)
    p_gr_sub.add_argument("--out", default=None)
    p_gr_sub.add_argument("--json", action="store_true")
    p_gr_sub.set_defaults(func=_cmd_graph_subgraph)

    # model
    p_mod = sub.add_parser("model", help="Inspect registered dynamical models and backends")
    mod_sub = p_mod.add_subparsers(dest="model_cmd", required=True)
    p_mod_list = mod_sub.add_parser("list", help="List models and CPU reference backend")
    p_mod_list.add_argument("--json", action="store_true")
    p_mod_list.set_defaults(func=_cmd_model_list)
    p_mod_val = mod_sub.add_parser("validate", help="Validate LIF model spec YAML/JSON")
    p_mod_val.add_argument("path")
    p_mod_val.add_argument("--json", action="store_true")
    p_mod_val.set_defaults(func=_cmd_model_validate)

    # protocol
    p_pr = sub.add_parser("protocol", help="Validate and freeze experiment protocols")
    pr_sub = p_pr.add_subparsers(dest="protocol_cmd", required=True)
    p_pr_val = pr_sub.add_parser("validate", help="Validate YAML protocol against schema & gates")
    p_pr_val.add_argument("path")
    p_pr_val.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Check structural schema only for draft protocols containing UNRESOLVED placeholders",
    )
    p_pr_val.add_argument("--json", action="store_true")
    p_pr_val.set_defaults(func=_cmd_protocol_validate)

    p_pr_frz = pr_sub.add_parser(
        "freeze",
        help="Write immutable frozen protocol YAML (requires --confirm-freeze)",
    )
    p_pr_frz.add_argument("path")
    p_pr_frz.add_argument("--out", default=None)
    p_pr_frz.add_argument(
        "--confirm-freeze",
        action="store_true",
        help="Explicit human confirmation required before freezing a protocol revision",
    )
    p_pr_frz.add_argument("--json", action="store_true")
    p_pr_frz.set_defaults(func=_cmd_protocol_freeze)

    # run
    p_run = sub.add_parser("run", help="Run simulation workflows")
    run_sub = p_run.add_subparsers(dest="run_cmd", required=True)
    p_run_demo = run_sub.add_parser(
        "synthetic-demo",
        help="Execute end-to-end Phase 0 synthetic vertical slice",
    )
    p_run_demo.add_argument("--work-dir", required=True)
    p_run_demo.add_argument("--seeds", type=int, default=5)
    p_run_demo.add_argument("--json", action="store_true")
    p_run_demo.set_defaults(func=_cmd_run_synthetic_demo)

    p_run_plan = run_sub.add_parser("plan", help="Dry-run protocol and estimate resources")
    p_run_plan.add_argument("--protocol", required=True)
    p_run_plan.add_argument("--dataset-dir", required=True)
    p_run_plan.add_argument("--replicates", type=int, default=None)
    p_run_plan.add_argument("--json", action="store_true")
    p_run_plan.set_defaults(func=_cmd_run_plan)

    p_run_start = run_sub.add_parser(
        "start", help="Launch isolated protocol run (with optional --detach)"
    )
    p_run_start.add_argument("--protocol", required=True)
    p_run_start.add_argument("--dataset-dir", required=True)
    p_run_start.add_argument("--work-dir", required=True)
    p_run_start.add_argument("--replicates", type=int, default=None)
    p_run_start.add_argument("--workers", type=int, default=1)
    p_run_start.add_argument("--detach", action="store_true")
    p_run_start.add_argument("--json", action="store_true")
    p_run_start.set_defaults(func=_cmd_run_start)

    p_run_status = run_sub.add_parser("status", help="Inspect local job and run statuses")
    p_run_status.add_argument("--work-dir", required=True)
    p_run_status.add_argument("--json", action="store_true")
    p_run_status.set_defaults(func=_cmd_run_status)

    p_run_cancel = run_sub.add_parser(
        "cancel", help="Cancel a running local job and mark incomplete artifacts cancelled"
    )
    p_run_cancel.add_argument("--work-dir", required=True)
    p_run_cancel.add_argument("--json", action="store_true")
    p_run_cancel.set_defaults(func=_cmd_run_cancel)

    # benchmark
    p_bm = sub.add_parser("benchmark", help="Run and evaluate published reproduction benchmarks")
    bm_sub = p_bm.add_subparsers(dest="benchmark_cmd", required=True)
    p_bm_rep = bm_sub.add_parser(
        "reproduce", help="Execute reproduction protocol and check targets"
    )
    p_bm_rep.add_argument("--protocol", required=True)
    p_bm_rep.add_argument("--dataset-dir", required=True)
    p_bm_rep.add_argument("--reference-targets", required=True)
    p_bm_rep.add_argument("--out-dir", required=True)
    p_bm_rep.add_argument("--replicates", type=int, default=None)
    p_bm_rep.add_argument("--workers", type=int, default=1)
    p_bm_rep.add_argument("--json", action="store_true")
    p_bm_rep.set_defaults(func=_cmd_benchmark_reproduce)

    # analysis
    p_an = sub.add_parser("analysis", help="Run paired statistical analysis over run artifacts")
    an_sub = p_an.add_subparsers(dest="analysis_cmd", required=True)
    p_an_run = an_sub.add_parser("run", help="Compute paired condition contrast")
    p_an_run.add_argument("--runs-dir", required=True)
    p_an_run.add_argument("--out", required=True)
    p_an_run.add_argument("--baseline", required=True)
    p_an_run.add_argument("--treatment", required=True)
    p_an_run.add_argument("--neuron-id", required=True)
    p_an_run.add_argument("--json", action="store_true")
    p_an_run.set_defaults(func=_cmd_analysis_run)

    # export
    p_ex = sub.add_parser("export", help="Export evidence-linked publication bundle")
    ex_sub = p_ex.add_subparsers(dest="export_cmd", required=True)
    p_ex_bun = ex_sub.add_parser(
        "bundle", help="Export SVG/PNG figure, source tables, and manifest"
    )
    p_ex_bun.add_argument("--analysis-dir", required=True)
    p_ex_bun.add_argument("--out", required=True)
    p_ex_bun.add_argument("--json", action="store_true")
    p_ex_bun.set_defaults(func=_cmd_export_bundle)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
