"""Published benchmark evaluation against predeclared reference tolerances."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


class BenchmarkError(ValueError):
    """Raised when benchmark artifacts are missing, heterogeneous, or invalid."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def evaluate_shiu2024_benchmark(
    runs_dir: Path,
    reference_targets_path: Path,
    out_dir: Path,
    *,
    expected_replicates_override: int | None = None,
) -> Path:
    """Compare completed simulation runs against predeclared Shiu et al. (2024) targets."""
    if not runs_dir.is_dir():
        raise BenchmarkError(f"runs_dir does not exist: {runs_dir}")
    if not reference_targets_path.is_file():
        raise BenchmarkError(f"reference_targets_path not found: {reference_targets_path}")

    ref = json.loads(reference_targets_path.read_text(encoding="utf-8"))
    ref_sha = _sha256_file(reference_targets_path)

    by_condition: dict[str, dict[int, tuple[Path, dict[str, Any], str]]] = defaultdict(dict)
    failed_runs: list[dict[str, Any]] = []
    provenance_anchor: dict[str, Any] | None = None

    for candidate in sorted(runs_dir.iterdir()):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "manifest.json"
        if not manifest_path.is_file():
            if (candidate / "spec.json").is_file() or (candidate / "logs").is_dir():
                failed_runs.append(
                    {
                        "run_id": candidate.name,
                        "status": "incomplete_no_manifest",
                        "condition_id": None,
                        "replicate_id": None,
                        "failure_reason": "Missing manifest.json",
                    }
                )
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_sha = _sha256_file(manifest_path)
        if manifest.get("status") != "succeeded" or not (candidate / "COMPLETE").is_file():
            failed_runs.append(
                {
                    "run_id": manifest.get("run_id", candidate.name),
                    "status": manifest.get("status", "incomplete"),
                    "condition_id": manifest.get("condition_id"),
                    "replicate_id": manifest.get("replicate_id"),
                    "failure_reason": manifest.get("failure_reason")
                    or "Missing COMPLETE marker or non-succeeded status",
                }
            )
            continue

        anchor = {
            "dataset_id": manifest["dataset_id"],
            "dataset_release": manifest["dataset_release"],
            "dataset_manifest_sha256": manifest["dataset_manifest_sha256"],
            "protocol_id": manifest["protocol_id"],
            "protocol_revision": manifest["protocol_revision"],
            "protocol_sha256": manifest["protocol_sha256"],
            "model_id": manifest["model_id"],
            "model_revision": manifest["model_revision"],
            "parameter_manifest_sha256": manifest["parameter_manifest_sha256"],
            "is_synthetic_fixture": manifest["is_synthetic_fixture"],
        }
        if provenance_anchor is None:
            provenance_anchor = anchor
        elif provenance_anchor != anchor:
            raise BenchmarkError(f"Heterogeneous run provenance detected in {candidate.name}")

        cond_id = str(manifest["condition_id"])
        rep_id = int(manifest["replicate_id"])
        if rep_id in by_condition[cond_id]:
            raise BenchmarkError(f"Duplicate succeeded replicate {rep_id} for {cond_id!r}")
        by_condition[cond_id][rep_id] = (candidate, manifest, manifest_sha)

    if provenance_anchor is None:
        raise BenchmarkError(f"No succeeded runs found in {runs_dir}")

    # Collect target metrics per condition
    condition_replicate_counts: dict[str, dict[str, Any]] = {}
    spike_control_checks: list[dict[str, Any]] = []
    target_comparisons: list[dict[str, Any]] = []
    rates_cache: dict[tuple[str, str], dict[int, float]] = {}

    for cond_id, cond_spec in ref["conditions"].items():
        reps_map = by_condition.get(cond_id, {})
        expected_reps = (
            int(cond_spec["expected_replicates"])
            if expected_replicates_override is None
            else int(expected_replicates_override)
        )
        observed_reps = len(reps_map)
        rep_ok = observed_reps >= expected_reps
        condition_replicate_counts[cond_id] = {
            "expected_replicates": expected_reps,
            "observed_replicates": observed_reps,
            "passed": rep_ok,
        }

        targets = cond_spec["targets"]
        target_ids = [str(t["neuron_id"]) for t in targets]
        per_target_vals: dict[str, dict[int, float]] = {tid: {} for tid in target_ids}
        max_spikes_observed = 0

        for rep_id, (run_dir, _, _) in sorted(reps_map.items()):
            qc_data = json.loads((run_dir / "qc.json").read_text(encoding="utf-8"))
            max_spikes_observed = max(max_spikes_observed, int(qc_data["total_spikes_in_window"]))

            metrics_df = pl.read_parquet(run_dir / "metrics.parquet").filter(
                pl.col("source_neuron_id").is_in(target_ids)
            )
            found = {
                str(r["source_neuron_id"]): float(r["firing_rate_hz"])
                for r in metrics_df.iter_rows(named=True)
            }
            for tid in target_ids:
                if tid not in found:
                    raise BenchmarkError(
                        f"Target neuron {tid!r} missing from {run_dir / 'metrics.parquet'}"
                    )
                per_target_vals[tid][rep_id] = found[tid]

        max_spikes_allowed = cond_spec.get("expected_max_total_spikes")
        if max_spikes_allowed is not None:
            spike_control_checks.append(
                {
                    "condition_id": cond_id,
                    "expected_max_total_spikes": int(max_spikes_allowed),
                    "observed_max_total_spikes": max_spikes_observed,
                    "passed": max_spikes_observed <= int(max_spikes_allowed) and rep_ok,
                }
            )

        for t_spec in targets:
            tid = str(t_spec["neuron_id"])
            rep_dict = per_target_vals[tid]
            rates_cache[(cond_id, tid)] = rep_dict
            vals = np.array([rep_dict[r] for r in sorted(rep_dict)], dtype=np.float64)
            obs_mean = float(np.mean(vals)) if len(vals) > 0 else float("nan")
            obs_sd_pop = float(np.std(vals, ddof=0)) if len(vals) > 0 else float("nan")
            obs_sd_sample = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            obs_se = obs_sd_sample / float(np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            ref_mean = float(t_spec["reference_mean_hz"])
            tol = float(t_spec["tolerance_abs_hz"])
            abs_diff = abs(obs_mean - ref_mean) if len(vals) > 0 else float("inf")
            passed = bool(rep_ok and np.isfinite(abs_diff) and abs_diff <= tol)
            target_comparisons.append(
                {
                    "condition_id": cond_id,
                    "neuron_id": tid,
                    "label": str(t_spec["label"]),
                    "n_replicates": len(vals),
                    "observed_mean_hz": obs_mean,
                    "observed_sd_pop_hz": obs_sd_pop,
                    "observed_sd_sample_hz": obs_sd_sample,
                    "observed_se_hz": obs_se,
                    "reference_mean_hz": ref_mean,
                    "reference_sd_pop_hz": float(t_spec["reference_sd_pop_hz"]),
                    "signed_diff_from_ref_hz": obs_mean - ref_mean
                    if len(vals) > 0
                    else float("nan"),
                    "abs_diff_from_ref_hz": abs_diff,
                    "tolerance_abs_hz": tol,
                    "passed": passed,
                }
            )

    contrast_comparisons: list[dict[str, Any]] = []
    for c_spec in ref.get("contrasts", []):
        b_cond = str(c_spec["baseline_condition"])
        t_cond = str(c_spec["treatment_condition"])
        tid = str(c_spec["neuron_id"])
        for c_key in (b_cond, t_cond):
            if (c_key, tid) not in rates_cache:
                c_vals: dict[int, float] = {}
                for rep_id, (run_dir, _, _) in sorted(by_condition.get(c_key, {}).items()):
                    m_df = pl.read_parquet(run_dir / "metrics.parquet").filter(
                        pl.col("source_neuron_id") == tid
                    )
                    if m_df.height == 1:
                        c_vals[rep_id] = float(m_df["firing_rate_hz"][0])
                rates_cache[(c_key, tid)] = c_vals
        b_map = rates_cache.get((b_cond, tid), {})
        t_map = rates_cache.get((t_cond, tid), {})
        paired_reps = sorted(set(b_map) & set(t_map))
        diffs = np.array([t_map[r] - b_map[r] for r in paired_reps], dtype=np.float64)
        mean_diff = float(np.mean(diffs)) if len(diffs) > 0 else float("nan")
        sd_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
        direction = str(c_spec["expected_direction"])
        if direction == "negative":
            dir_ok = bool(len(diffs) > 0 and mean_diff < 0.0)
        elif direction == "positive":
            dir_ok = bool(len(diffs) > 0 and mean_diff > 0.0)
        else:
            raise BenchmarkError(f"Unsupported contrast expected_direction {direction!r}")
        contrast_comparisons.append(
            {
                "contrast_id": str(c_spec["contrast_id"]),
                "baseline_condition": b_cond,
                "treatment_condition": t_cond,
                "neuron_id": tid,
                "n_pairs": len(paired_reps),
                "observed_mean_diff_hz": mean_diff,
                "observed_sd_diff_hz": sd_diff,
                "reference_mean_diff_hz": float(c_spec["reference_mean_diff_hz"]),
                "expected_direction": direction,
                "passed": dir_ok,
            }
        )

    overall_passed = (
        len(failed_runs) == 0
        and all(v["passed"] for v in condition_replicate_counts.values())
        and all(c["passed"] for c in spike_control_checks)
        and all(t["passed"] for t in target_comparisons)
        and all(c["passed"] for c in contrast_comparisons)
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    comp_pq = out_dir / "benchmark_comparison.parquet"
    pl.DataFrame(target_comparisons).write_parquet(comp_pq)

    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "benchmark_id": ref["benchmark_id"],
        "reference_targets_sha256": ref_sha,
        "provenance": provenance_anchor,
        "overall_passed": overall_passed,
        "failed_run_count": len(failed_runs),
        "failed_runs": failed_runs,
        "condition_replicate_counts": condition_replicate_counts,
        "spike_control_checks": spike_control_checks,
        "target_comparisons": target_comparisons,
        "contrast_comparisons": contrast_comparisons,
        "artifacts": {
            "benchmark_comparison.parquet": _sha256_file(comp_pq),
        },
    }
    report_path = out_dir / "benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Write concise factual markdown summary
    table_lines = [
        "| Condition | Neuron | Label | N | SYNAPSE Mean ± SD (Hz) "
        "| Ref Mean ± SD (Hz) | |Δ| (Hz) | Tol (Hz) | Pass |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in target_comparisons:
        table_lines.append(
            f"| `{row['condition_id']}` | `{row['neuron_id']}` | {row['label']} | "
            f"{row['n_replicates']} | "
            f"{row['observed_mean_hz']:.3f} ± {row['observed_sd_pop_hz']:.3f} | "
            f"{row['reference_mean_hz']:.3f} ± {row['reference_sd_pop_hz']:.3f} | "
            f"{row['abs_diff_from_ref_hz']:.3f} | {row['tolerance_abs_hz']:.1f} | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
        )

    contrast_lines = [
        f"- `{c['contrast_id']}` (`{c['treatment_condition']} - {c['baseline_condition']}`): "
        f"`{c['observed_mean_diff_hz']:+.3f}` Hz (SD `{c['observed_sd_diff_hz']:.3f}` Hz, "
        f"ref `{c['reference_mean_diff_hz']:+.3f}` Hz, expected `{c['expected_direction']}` -> "
        f"{'PASS' if c['passed'] else 'FAIL'})"
        for c in contrast_comparisons
    ]

    summary_md = out_dir / "BENCHMARK_SUMMARY.md"
    summary_md.write_text(
        f"# {ref['benchmark_id']} Report\n\n"
        f"- **Overall Passed:** `{overall_passed}`\n"
        f"- **Dataset:** `{provenance_anchor['dataset_id']}` "
        f"`{provenance_anchor['dataset_release']}` "
        f"(manifest `{provenance_anchor['dataset_manifest_sha256']}`)\n"
        f"- **Model:** `{provenance_anchor['model_id']}` v`{provenance_anchor['model_revision']}` "
        f"(params `{provenance_anchor['parameter_manifest_sha256']}`)\n"
        f"- **Failed / Incomplete Runs:** `{len(failed_runs)}`\n\n"
        f"## Target Rate Comparisons\n\n"
        + "\n".join(table_lines)
        + "\n\n## Directional Contrasts\n\n"
        + "\n".join(contrast_lines)
        + "\n",
        encoding="utf-8",
    )
    return report_path
