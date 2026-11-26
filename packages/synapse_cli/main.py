"""CLI entrypoints calling SYNAPSE scientific packages directly (offline-safe)."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from synapse_analysis import run_paired_analysis
from synapse_core import (
    Brian2CPUBackend,
    CircadianHomeostaticParameters,
    LIFParameters,
    MBPlasticityParameters,
    PlasticityTrajectory,
    TopologyAnalysisParameters,
    TwoProcessTrajectory,
    extract_bounded_subgraph,
    run_conditioning_paradigm,
    run_progressive_ablation_curve,
    run_shift_work_experiment,
    simulate_conditioning_schedule,
    validate_model_spec,
    verify_circadian_homeostatic_gates,
    verify_plasticity_paradigm_gates,
    verify_topology_ablation_gates,
)
from synapse_data import (
    build_default_registry,
    ingest_synthetic_fixture,
    validate_canonical_dataset,
)
from synapse_experiments import (
    cancel_local_job,
    collect_source_provenance,
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
    plasticity_l2 = MBPlasticityParameters()
    circadian_l3 = CircadianHomeostaticParameters()
    topology_l0 = TopologyAnalysisParameters()
    backend = Brian2CPUBackend()
    caps = backend.capabilities()
    payload = {
        "models": [
            {
                "model_id": topology_l0.model_id,
                "model_revision": topology_l0.model_revision,
                "model_level": topology_l0.model_level,
                "parameter_manifest_sha256": topology_l0.canonical_sha256(),
                "solver": "csgraph_dijkstra",
                "dt_s": 0.0,
                "parameter_source": topology_l0.parameter_source,
            },
            {
                "model_id": default_lif.model_id,
                "model_revision": default_lif.model_revision,
                "model_level": "L1",
                "parameter_manifest_sha256": default_lif.canonical_sha256(),
                "solver": default_lif.solver,
                "dt_s": default_lif.dt_s,
                "dg_unless_refractory": default_lif.dg_unless_refractory,
                "parameter_source": default_lif.parameter_source,
            },
            {
                "model_id": shiu_lif.model_id,
                "model_revision": shiu_lif.model_revision,
                "model_level": "L1",
                "parameter_manifest_sha256": shiu_lif.canonical_sha256(),
                "solver": shiu_lif.solver,
                "dt_s": shiu_lif.dt_s,
                "dg_unless_refractory": shiu_lif.dg_unless_refractory,
                "parameter_source": shiu_lif.parameter_source,
            },
            {
                "model_id": plasticity_l2.model_id,
                "model_revision": plasticity_l2.model_revision,
                "model_level": plasticity_l2.model_level,
                "parameter_manifest_sha256": plasticity_l2.canonical_sha256(),
                "solver": plasticity_l2.solver,
                "dt_s": plasticity_l2.dt_s,
                "parameter_source": plasticity_l2.parameter_source,
            },
            {
                "model_id": circadian_l3.model_id,
                "model_revision": circadian_l3.model_revision,
                "model_level": circadian_l3.model_level,
                "parameter_manifest_sha256": circadian_l3.canonical_sha256(),
                "solver": circadian_l3.solver,
                "dt_s": circadian_l3.dt_eval_h * circadian_l3.seconds_per_hour,
                "parameter_source": circadian_l3.parameter_source,
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


def _write_l3_prc_figure(gate_report: dict[str, Any], figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    curve = gate_report["gates"]["light_pulse_prc"]["curve"]
    cts = [int(row["ct_hours"]) for row in curve]
    shifts = [float(row["phase_shift_h"] or 0.0) for row in curve]
    colors = ["#009E73" if s > 0.15 else ("#D55E00" if s < -0.15 else "#64748B") for s in shifts]

    fig = Figure(figsize=(7.2, 4.4), dpi=200)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.axhline(0.0, color="#475569", linewidth=1.0, linestyle="--")
    ax.axvspan(0, 12, color="#FEF3C7", alpha=0.45, label="Subjective day (CT 0-12)")
    ax.axvspan(12, 24, color="#E2E8F0", alpha=0.45, label="Subjective night (CT 12-24)")
    ax.plot(cts, shifts, color="#0072B2", linewidth=1.8, zorder=2)
    ax.scatter(cts, shifts, c=colors, s=55, zorder=3)
    ax.set_xlim(-0.5, 22.5)
    ax.set_xticks(cts)
    ax.set_xlabel("Circadian Time of 2 h Light Pulse (CT, hours)")
    ax.set_ylabel("Phase Shift (+ advance / - delay, hours)")
    ax.set_title(
        "L3 Circadian Light-Pulse PRC (BIOMD0000000021; RUO)",
        fontsize=11,
        fontweight="bold",
    )
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures_dir / "l3_prc_curve.svg")
    fig.savefig(figures_dir / "l3_prc_curve.png", dpi=200)


def _write_l3_shift_work_figure(
    summary: dict[str, Any],
    trajectories: dict[str, TwoProcessTrajectory],
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig = Figure(figsize=(8.6, 5.4), dpi=200)
    FigureCanvasAgg(fig)
    ax_s = fig.add_subplot(211)
    ax_err = fig.add_subplot(212)

    palette = {
        "ld12_12_control": "#0072B2",
        "deprivation_12h_recovery": "#D55E00",
        "shift_delay_8h": "#009E73",
        "shift_advance_6h": "#CC79A7",
        "rotating_shift_8h": "#E69F00",
    }

    for arm_id in ("ld12_12_control", "deprivation_12h_recovery"):
        traj = trajectories[arm_id]
        mask = traj.times_h >= 120.0
        ax_s.plot(
            traj.times_h[mask] / 24.0,
            traj.s_homeostat[mask],
            label=arm_id,
            color=palette[arm_id],
            linewidth=1.5,
        )
    ax_s.axvspan(156.0 / 24.0, 168.0 / 24.0, color="#FCA5A5", alpha=0.35, label="12 h forced wake")
    ax_s.set_ylabel("Homeostat S (norm.)")
    ax_s.set_title(
        "L3 Two-Process Homeostat & Shift-Work Misalignment (tau_i=8.76h, tau_d=9.51h; RUO)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_s.legend(loc="upper right", frameon=False, fontsize=8)
    ax_s.spines["top"].set_visible(False)
    ax_s.spines["right"].set_visible(False)

    for arm_id in ("ld12_12_control", "shift_delay_8h", "shift_advance_6h", "rotating_shift_8h"):
        errs = summary["arms"][arm_id]["post_onset_phase_errors"]
        if not errs:
            continue
        ax_err.plot(
            [e["day"] for e in errs],
            [abs(float(e["phase_error_h"])) for e in errs],
            marker="o",
            markersize=3.8,
            linewidth=1.5,
            color=palette[arm_id],
            label=arm_id,
        )
    ax_err.axhline(
        1.0, color="#64748B", linestyle="--", linewidth=1.0, label="1.0 h re-entrainment"
    )
    ax_err.set_xlabel("Simulation Day (24 h cycles)")
    ax_err.set_ylabel("|Phase Error| (hours)")
    ax_err.legend(loc="upper right", frameon=False, fontsize=8, ncol=2)
    ax_err.spines["top"].set_visible(False)
    ax_err.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(figures_dir / "l3_shift_work_dynamics.svg")
    fig.savefig(figures_dir / "l3_shift_work_dynamics.png", dpi=200)


def _cmd_circadian_verify(args: argparse.Namespace) -> int:
    params = CircadianHomeostaticParameters()
    report = verify_circadian_homeostatic_gates(params)
    report["generated_at_utc"] = datetime.now(UTC).isoformat()
    report["source_provenance"] = collect_source_provenance(_repo_root())
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "l3_verification_gate.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        _write_l3_prc_figure(report, out_dir / "figures")
    _emit(report, as_json=args.json)
    return 0 if report["overall_passed"] else 3


def _cmd_circadian_shift_work(args: argparse.Namespace) -> int:
    params = CircadianHomeostaticParameters()
    summary, trajectories = run_shift_work_experiment(params, require_verified_gate=True)
    summary["generated_at_utc"] = datetime.now(UTC).isoformat()
    summary["source_provenance"] = collect_source_provenance(_repo_root())
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "l3_shift_work_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        # Downsample strictly at 0.25 h (every 5th 0.05 h step) for compact archival timeseries
        rows_df_parts: list[pl.DataFrame] = []
        for arm_id, traj in trajectories.items():
            sl = slice(None, None, 5)
            rows_df_parts.append(
                pl.DataFrame(
                    {
                        "arm_id": [arm_id] * int(traj.times_h[sl].size),
                        "time_h": traj.times_h[sl],
                        "light": traj.light[sl],
                        "p_total_nm": traj.p_total[sl],
                        "c_nuc_nm": traj.c_n[sl],
                        "c_wake": traj.c_wake[sl],
                        "s_homeostat": traj.s_homeostat[sl],
                        "u_threshold": traj.u_threshold[sl],
                        "l_threshold": traj.l_threshold[sl],
                        "modeled_rest_state": traj.modeled_rest_state[sl].astype(int),
                    }
                )
            )
        pl.concat(rows_df_parts).write_parquet(out_dir / "l3_timeseries.parquet")
        _write_l3_shift_work_figure(summary, trajectories, out_dir / "figures")
    _emit(summary, as_json=args.json)
    return 0


def _write_l2_controls_figure(
    params: MBPlasticityParameters,
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    arms = (
        "paired_conditioning",
        "spontaneous_recovery_only",
        "yoked_unpaired",
        "sham_no_stimulus",
        "dan_blocked",
    )
    colors = {
        "paired_conditioning": "#0072B2",
        "spontaneous_recovery_only": "#009E73",
        "yoked_unpaired": "#E69F00",
        "sham_no_stimulus": "#64748B",
        "dan_blocked": "#CC79A7",
    }
    phase_times = [("Acq (145s)", 145.0), ("Ext (235s)", 235.0), ("Reinst (310s)", 310.0)]

    trajs = {arm: simulate_conditioning_schedule(params, arm_id=arm) for arm in arms}
    fig = Figure(figsize=(8.0, 4.4), dpi=200)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    xs = [0.0, 1.0, 2.0]
    width = 0.15
    for idx, arm in enumerate(arms):
        offset = (idx - 2.0) * width
        vals = []
        for _, t_val in phase_times:
            t_idx = int((abs(trajs[arm].times_s - t_val)).argmin())
            vals.append(float(trajs[arm].pi_proxy[t_idx]))
        ax.bar(
            [x + offset for x in xs],
            vals,
            width=width,
            color=colors[arm],
            label=arm,
        )
    ax.axhline(0.0, color="#475569", linewidth=1.0, linestyle="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([label for label, _ in phase_times])
    ax.set_ylabel("Learned Preference Proxy (PI)")
    ax.set_title(
        "L2 MB Plasticity Conditioning vs Negative Controls (RUO)",
        fontsize=11,
        fontweight="bold",
    )
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures_dir / "l2_controls_comparison.svg")
    fig.savefig(figures_dir / "l2_controls_comparison.png", dpi=200)


def _write_l2_learning_curve_figure(
    trajectories: dict[str, PlasticityTrajectory],
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig = Figure(figsize=(8.6, 5.4), dpi=200)
    FigureCanvasAgg(fig)
    ax_pi = fig.add_subplot(211)
    ax_w = fig.add_subplot(212)

    palette = {
        "paired_conditioning": "#0072B2",
        "spontaneous_recovery_only": "#009E73",
        "yoked_unpaired": "#E69F00",
        "sham_no_stimulus": "#64748B",
        "dan_blocked": "#CC79A7",
    }
    for arm_id, traj in trajectories.items():
        ax_pi.plot(
            traj.times_s,
            traj.pi_proxy,
            label=arm_id,
            color=palette.get(arm_id, "#0072B2"),
            linewidth=1.6,
        )
    ax_pi.axvspan(10.0, 102.0, color="#DBEAFE", alpha=0.35, label="Acq cues")
    ax_pi.axvspan(150.0, 220.0, color="#FEE2E2", alpha=0.35, label="Extinction")
    ax_pi.axvspan(265.0, 290.0, color="#DCFCE7", alpha=0.35, label="Reinstatement PAM")
    ax_pi.set_ylabel("Preference Index (PI)")
    ax_pi.set_title(
        "L2 MB Three-Factor Plasticity: Acquisition, Parallel Extinction & Reinstatement (RUO)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_pi.legend(loc="upper right", frameon=False, fontsize=7.5, ncol=2)
    ax_pi.spines["top"].set_visible(False)
    ax_pi.spines["right"].set_visible(False)

    paired = trajectories["paired_conditioning"]
    ax_w.plot(
        paired.times_s,
        paired.w_avoid_cs_plus,
        color="#D55E00",
        linewidth=1.8,
        label="w_avoid (CS+)",
    )
    ax_w.plot(
        paired.times_s,
        paired.w_appr_cs_plus,
        color="#0072B2",
        linewidth=1.8,
        label="w_appr (CS+)",
    )
    ax_w.plot(
        paired.times_s,
        paired.w_avoid_cs_minus,
        color="#009E73",
        linewidth=1.5,
        linestyle="--",
        label="w_avoid (CS-)",
    )
    ax_w.set_xlabel("Time (seconds)")
    ax_w.set_ylabel("Synaptic Weight (norm.)")
    ax_w.set_ylim(0.1, 1.05)
    ax_w.legend(loc="lower right", frameon=False, fontsize=8, ncol=3)
    ax_w.spines["top"].set_visible(False)
    ax_w.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(figures_dir / "l2_learning_curve.svg")
    fig.savefig(figures_dir / "l2_learning_curve.png", dpi=200)


def _cmd_plasticity_verify(args: argparse.Namespace) -> int:
    params = MBPlasticityParameters()
    report = verify_plasticity_paradigm_gates(params)
    report["generated_at_utc"] = datetime.now(UTC).isoformat()
    report["source_provenance"] = collect_source_provenance(_repo_root())
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "l2_verification_gate.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        _write_l2_controls_figure(params, out_dir / "figures")
    _emit(report, as_json=args.json)
    return 0 if report["overall_passed"] else 3


def _cmd_plasticity_paradigm(args: argparse.Namespace) -> int:
    params = MBPlasticityParameters()
    summary, trajectories = run_conditioning_paradigm(params, require_verified_gate=True)
    summary["generated_at_utc"] = datetime.now(UTC).isoformat()
    summary["source_provenance"] = collect_source_provenance(_repo_root())
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "l2_paradigm_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        # Downsample strictly at 0.5 s (every 10th 0.05 s step) for compact archival timeseries
        parts: list[pl.DataFrame] = []
        for arm_id, traj in trajectories.items():
            sl = slice(None, None, 10)
            parts.append(
                pl.DataFrame(
                    {
                        "arm_id": [arm_id] * int(traj.times_s[sl].size),
                        "time_s": traj.times_s[sl],
                        "r_kc_cs_plus": traj.r_kc_cs_plus[sl],
                        "r_kc_cs_minus": traj.r_kc_cs_minus[sl],
                        "u_reward": traj.u_reward[sl],
                        "d_pam": traj.d_pam[sl],
                        "d_ppl1": traj.d_ppl1[sl],
                        "w_avoid_cs_plus": traj.w_avoid_cs_plus[sl],
                        "w_avoid_cs_minus": traj.w_avoid_cs_minus[sl],
                        "w_appr_cs_plus": traj.w_appr_cs_plus[sl],
                        "w_appr_cs_minus": traj.w_appr_cs_minus[sl],
                        "pi_proxy": traj.pi_proxy[sl],
                    }
                )
            )
        pl.concat(parts).write_parquet(out_dir / "l2_timeseries.parquet")
        _write_l2_learning_curve_figure(trajectories, out_dir / "figures")
    _emit(summary, as_json=args.json)
    return 0


def _write_l0_attack_curve_figure(
    attack_summary: dict[str, Any],
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    pts = attack_summary["curve_points"]
    tgt_pts = sorted(
        [p for p in pts if p["arm_type"] == "targeted_cell_loss"], key=lambda r: r["step_k"]
    )
    ctrl_pts = sorted(
        [p for p in pts if p["arm_type"] == "matched_random_cell_loss"], key=lambda r: r["step_k"]
    )

    fig = Figure(figsize=(8.2, 4.6), dpi=200)
    FigureCanvasAgg(fig)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)

    xs_t = [p["step_k"] for p in tgt_pts]
    xs_c = [p["step_k"] for p in ctrl_pts]
    ax1.plot(
        xs_t,
        [p["weighted_eff_ratio"] for p in tgt_pts],
        marker="o",
        linewidth=2.0,
        color="#D55E00",
        label="Targeted hub loss",
    )
    ax1.plot(
        xs_c,
        [p["weighted_eff_ratio"] for p in ctrl_pts],
        marker="s",
        linewidth=2.0,
        linestyle="--",
        color="#0072B2",
        label="Matched-random ctrl",
    )
    ax1.set_ylim(0.0, 1.08)
    ax1.set_xticks(xs_t)
    ax1.set_xlabel("Ablated neurons (k)")
    ax1.set_ylabel("Weighted pathway efficiency ratio")
    ax1.set_title("Pathway Efficiency vs Cell Loss", fontsize=10, fontweight="bold")
    ax1.legend(loc="lower left", frameon=False, fontsize=8)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2.plot(
        xs_t,
        [p["three_hop_flow_ratio"] for p in tgt_pts],
        marker="o",
        linewidth=2.0,
        color="#D55E00",
        label="Targeted hub loss",
    )
    ax2.plot(
        xs_c,
        [p["three_hop_flow_ratio"] for p in ctrl_pts],
        marker="s",
        linewidth=2.0,
        linestyle="--",
        color="#0072B2",
        label="Matched-random ctrl",
    )
    ax2.set_ylim(0.0, 1.08)
    ax2.set_xticks(xs_t)
    ax2.set_xlabel("Ablated neurons (k)")
    ax2.set_ylabel("3-hop exc flow ratio")
    ax2.set_title("Multi-Hop Throughput Retention", fontsize=10, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle(
        f"L0 Progressive Connectome Attack ({attack_summary['dataset_id']}, RUO)",
        fontsize=11,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(figures_dir / "l0_attack_curve.svg")
    fig.savefig(figures_dir / "l0_attack_curve.png", dpi=200)


def _write_l0_ablation_dissociation_figure(
    attack_summary: dict[str, Any],
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    pts = attack_summary["curve_points"]
    syn_arms = attack_summary["synapse_ablation_arms"]
    k12_tgt = next(
        p for p in pts if p["arm_type"] == "targeted_cell_loss" and int(p["step_k"]) == 12
    )
    k12_ctrl = next(
        p for p in pts if p["arm_type"] == "matched_random_cell_loss" and int(p["step_k"]) == 12
    )
    items = [
        ("Intact", attack_summary["baseline"]),
        ("Ctrl Cells (k=12)", k12_ctrl),
        ("Hub Syn 50%", syn_arms["targeted_synapse_loss_50pct"]),
        ("Hub Syn 100%", syn_arms["targeted_synapse_loss_100pct"]),
        ("Hub Cells (k=12)", k12_tgt),
    ]
    if "matched_random_synapse_loss" in syn_arms:
        items.insert(2, ("Ctrl Syn 100%", syn_arms["matched_random_synapse_loss"]))

    labels = [x[0] for x in items]
    eff_vals = [float(x[1]["weighted_eff_ratio"]) for x in items]
    flow_vals = [float(x[1]["three_hop_flow_ratio"]) for x in items]
    xs = list(range(len(labels)))
    width = 0.36

    fig = Figure(figsize=(8.4, 4.5), dpi=200)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.bar(
        [x - width / 2 for x in xs],
        eff_vals,
        width=width,
        color="#0072B2",
        label="Weighted efficiency ratio",
    )
    ax.bar(
        [x + width / 2 for x in xs],
        flow_vals,
        width=width,
        color="#D55E00",
        label="3-hop flow ratio",
    )
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8.5)
    ax.set_ylim(0.0, 1.12)
    ax.set_ylabel("Retention ratio vs intact baseline")
    ax.set_title(
        f"L0 Cell Loss vs Synapse Loss Dissociation ({attack_summary['dataset_id']}, RUO)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures_dir / "l0_ablation_dissociation.svg")
    fig.savefig(figures_dir / "l0_ablation_dissociation.png", dpi=200)


def _cmd_topology_verify(args: argparse.Namespace) -> int:
    params = TopologyAnalysisParameters()
    report = verify_topology_ablation_gates(params)
    report["generated_at_utc"] = datetime.now(UTC).isoformat()
    report["source_provenance"] = collect_source_provenance(_repo_root())
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "l0_verification_gate.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
    _emit(report, as_json=args.json)
    return 0 if report["overall_passed"] else 3


def _cmd_topology_attack(args: argparse.Namespace) -> int:
    params = TopologyAnalysisParameters()
    gate_report = verify_topology_ablation_gates(params)
    if not gate_report["overall_passed"]:
        _emit(gate_report, as_json=args.json)
        return 3

    targets_doc = json.loads(Path(args.targets_json).read_text(encoding="utf-8"))
    graph, manifest, manifest_sha = load_graph_from_dataset(Path(args.dataset_dir))
    src_ids = targets_doc.get("source_sugar_grn_ids") or targets_doc["source_neuron_ids"]
    tgt_ids = targets_doc.get("readout_mn9_ids") or targets_doc["target_neuron_ids"]
    hub_ids = targets_doc["targeted_premotor_hub_ids"]
    ctrl_ids = targets_doc["matched_control_neuron_ids"]
    ctrl_syn = targets_doc.get("matched_control_synapse_ablation") or {}
    ctrl_syn_pre = ctrl_syn.get("pre_neuron_ids") or ()
    ctrl_syn_post = ctrl_syn.get("post_neuron_ids") or ()

    attack_full = run_progressive_ablation_curve(
        graph,
        source_neuron_ids=src_ids,
        target_neuron_ids=tgt_ids,
        targeted_hub_ids=hub_ids,
        matched_control_ids=ctrl_ids,
        ctrl_syn_pre_ids=ctrl_syn_pre,
        ctrl_syn_post_ids=ctrl_syn_post,
        params=params,
    )
    now_utc = datetime.now(UTC).isoformat()
    src_prov = collect_source_provenance(_repo_root())
    gate_report["generated_at_utc"] = now_utc
    gate_report["source_provenance"] = src_prov

    def _strip_edge_sample(pt: dict[str, Any]) -> dict[str, Any]:
        audit_slim = {k: v for k, v in pt["audit"].items() if k != "removed_edges_sample"}
        return {**pt, "audit": audit_slim}

    summary_payload = {
        "schema_version": attack_full["schema_version"],
        "model_id": attack_full["model_id"],
        "model_level": attack_full["model_level"],
        "parameter_manifest_sha256": attack_full["parameter_manifest_sha256"],
        "dataset_id": attack_full["dataset_id"],
        "release": str(manifest["release"]),
        "specimen_id": attack_full["specimen_id"],
        "dataset_manifest_sha256": manifest_sha,
        "source_graph_sha256": attack_full["source_graph_sha256"],
        "generated_at_utc": now_utc,
        "source_provenance": src_prov,
        "gate_overall_passed": bool(gate_report["overall_passed"]),
        "baseline": _strip_edge_sample(attack_full["baseline"]),
        "curve_points": [_strip_edge_sample(p) for p in attack_full["curve_points"]],
        "synapse_ablation_arms": {
            k: _strip_edge_sample(v) for k, v in attack_full["synapse_ablation_arms"].items()
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "l0_verification_gate.json").write_text(
        json.dumps(gate_report, indent=2),
        encoding="utf-8",
    )
    (out_dir / "l0_ablation_summary.json").write_text(
        json.dumps(summary_payload, indent=2),
        encoding="utf-8",
    )
    (out_dir / "l0_ablation_audit.json").write_text(
        json.dumps(attack_full, indent=2),
        encoding="utf-8",
    )
    curve_rows = [
        {
            "arm_type": p["arm_type"],
            "step_k": int(p["step_k"]),
            "ablation_id": p["ablation_id"],
            "removed_node_count": int(p["removed_node_count"]),
            "removed_edge_count": int(p["removed_edge_count"]),
            "removed_synapse_count": float(p["removed_synapse_count"]),
            "weighted_eff_ratio": float(p["weighted_eff_ratio"]),
            "three_hop_flow_ratio": float(p["three_hop_flow_ratio"]),
            "target_exc_syn_retention": float(p["target_exc_syn_retention"]),
            "largest_wcc_fraction": float(p["metrics"]["largest_wcc_fraction"]),
            "largest_scc_fraction": float(p["metrics"]["largest_scc_fraction"]),
            "reachability_fraction": float(p["metrics"]["reachability_fraction"]),
        }
        for p in [
            *attack_full["curve_points"],
            *attack_full["synapse_ablation_arms"].values(),
        ]
    ]
    pl.DataFrame(curve_rows).write_parquet(out_dir / "l0_attack_curve.parquet")
    _write_l0_attack_curve_figure(summary_payload, out_dir / "figures")
    _write_l0_ablation_dissociation_figure(summary_payload, out_dir / "figures")
    _emit(summary_payload, as_json=args.json)
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

    # circadian (Phase 5B L3 oscillator verification & gated shift-work schedules)
    p_circ = sub.add_parser(
        "circadian", help="Verify L3 circadian-homeostatic oscillator and run gated schedules"
    )
    circ_sub = p_circ.add_subparsers(dest="circadian_cmd", required=True)
    p_circ_ver = circ_sub.add_parser(
        "verify", help="Verify DD period, LD entrainment, light PRC, and deprivation rebound gates"
    )
    p_circ_ver.add_argument("--out-dir", default=None)
    p_circ_ver.add_argument("--json", action="store_true")
    p_circ_ver.set_defaults(func=_cmd_circadian_verify)

    p_circ_sw = circ_sub.add_parser(
        "shift-work", help="Run gated L3 shift-work & forced-wake schedules after verification"
    )
    p_circ_sw.add_argument("--out-dir", default=None)
    p_circ_sw.add_argument("--json", action="store_true")
    p_circ_sw.set_defaults(func=_cmd_circadian_shift_work)

    # plasticity (Phase 5B Addiction L2 MB plasticity verification & conditioning paradigm)
    p_plas = sub.add_parser(
        "plasticity", help="Verify L2 MB plasticity rules and run conditioning paradigms"
    )
    plas_sub = p_plas.add_subparsers(dest="plasticity_cmd", required=True)
    p_plas_ver = plas_sub.add_parser(
        "verify", help="Verify RK4 convergence, acquisition, extinction, reinstatement & controls"
    )
    p_plas_ver.add_argument("--out-dir", default=None)
    p_plas_ver.add_argument("--json", action="store_true")
    p_plas_ver.set_defaults(func=_cmd_plasticity_verify)

    p_plas_par = plas_sub.add_parser(
        "paradigm", help="Run gated L2 conditioning + control arms and export L2->L1 snapshots"
    )
    p_plas_par.add_argument("--out-dir", default=None)
    p_plas_par.add_argument("--json", action="store_true")
    p_plas_par.set_defaults(func=_cmd_plasticity_paradigm)

    # topology (Phase 5C Neuro L0 graph fragmentation & exact cell/synapse ablation audit)
    p_topo = sub.add_parser(
        "topology", help="Verify L0 graph ablation rules and run progressive attack curves"
    )
    topo_sub = p_topo.add_subparsers(dest="topology_cmd", required=True)
    p_topo_ver = topo_sub.add_parser(
        "verify", help="Verify L0 fragmentation, bridge dissociation & reverse Dijkstra parity"
    )
    p_topo_ver.add_argument("--out-dir", default=None)
    p_topo_ver.add_argument("--json", action="store_true")
    p_topo_ver.set_defaults(func=_cmd_topology_verify)

    p_topo_att = topo_sub.add_parser(
        "attack", help="Run gated L0 progressive attack curve & exact edge ablation audit"
    )
    p_topo_att.add_argument("--dataset-dir", required=True)
    p_topo_att.add_argument("--targets-json", required=True)
    p_topo_att.add_argument("--out-dir", required=True)
    p_topo_att.add_argument("--json", action="store_true")
    p_topo_att.set_defaults(func=_cmd_topology_attack)

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
