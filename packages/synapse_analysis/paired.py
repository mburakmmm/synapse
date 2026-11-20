"""Paired seed-ensemble analysis with transparent failed-run accounting."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from synapse_analysis.stats import paired_permutation_test


class AnalysisError(ValueError):
    """Raised when run artifacts are missing, inconsistent, or insufficient for analysis."""


def sha256_file(path: Path) -> str:
    """Compute streaming SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _summarize_values(values: np.ndarray) -> dict[str, float | int]:
    n = len(values)
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
    q25 = float(np.percentile(values, 25))
    median = float(np.percentile(values, 50))
    q75 = float(np.percentile(values, 75))
    return {
        "n_seed_replicates": n,
        "mean_hz": mean,
        "sd_hz": sd,
        "median_hz": median,
        "q25_hz": q25,
        "q75_hz": q75,
        "iqr_hz": q75 - q25,
    }


def run_paired_analysis(
    runs_dir: Path,
    out_dir: Path,
    *,
    baseline_condition: str,
    treatment_condition: str,
    target_neuron_id: str,
    seed_bootstrap: int = 0,
    n_bootstrap: int = 2000,
) -> Path:
    """Compute paired condition differences across simulation seeds from run artifacts."""
    if not runs_dir.is_dir():
        raise AnalysisError(f"runs_dir does not exist: {runs_dir}")

    succeeded_runs: list[tuple[Path, dict[str, Any], str]] = []
    failed_runs: list[dict[str, Any]] = []

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
        manifest_sha = sha256_file(manifest_path)
        has_complete = (candidate / "COMPLETE").is_file()
        if manifest.get("status") != "succeeded" or not has_complete:
            failed_runs.append(
                {
                    "run_id": manifest.get("run_id", candidate.name),
                    "status": manifest.get("status", "incomplete")
                    if has_complete
                    else f"{manifest.get('status', 'unknown')}_no_complete_marker",
                    "condition_id": manifest.get("condition_id"),
                    "replicate_id": manifest.get("replicate_id"),
                    "failure_reason": manifest.get("failure_reason")
                    or "Missing COMPLETE marker or non-succeeded status",
                }
            )
            continue

        succeeded_runs.append((candidate, manifest, manifest_sha))

    baseline_by_rep: dict[int, tuple[float, str, str]] = {}
    treatment_by_rep: dict[int, tuple[float, str, str]] = {}
    provenance_anchor: dict[str, Any] | None = None

    for run_dir, manifest, manifest_sha in succeeded_runs:
        cond = str(manifest["condition_id"])
        if cond not in (baseline_condition, treatment_condition):
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
            "analysis_intent": manifest["analysis_intent"],
        }
        if provenance_anchor is None:
            provenance_anchor = anchor
        elif provenance_anchor != anchor:
            raise AnalysisError(
                f"Heterogeneous run provenance in {run_dir.name}: "
                "cannot pool incompatible datasets/models/protocols"
            )

        metrics_path = run_dir / "metrics.parquet"
        if not metrics_path.is_file():
            raise AnalysisError(f"Missing metrics.parquet in succeeded run {run_dir}")
        df = pl.read_parquet(metrics_path)
        target_rows = df.filter(pl.col("source_neuron_id") == target_neuron_id)
        if target_rows.height != 1:
            raise AnalysisError(
                f"Expected 1 row for target_neuron_id={target_neuron_id!r} in {run_dir}, "
                f"found {target_rows.height}"
            )
        rate_hz = float(target_rows["firing_rate_hz"][0])
        rep_id = int(manifest["replicate_id"])
        run_id = str(manifest["run_id"])

        target_map = baseline_by_rep if cond == baseline_condition else treatment_by_rep
        if rep_id in target_map:
            raise AnalysisError(f"Duplicate replicate_id={rep_id} for condition={cond!r}")
        target_map[rep_id] = (rate_hz, run_id, manifest_sha)

    if provenance_anchor is None:
        raise AnalysisError(
            f"No succeeded runs found for conditions {baseline_condition!r} and "
            f"{treatment_condition!r} in {runs_dir}"
        )

    paired_reps = sorted(set(baseline_by_rep) & set(treatment_by_rep))
    if not paired_reps:
        raise AnalysisError(
            f"No matching paired replicate_ids between {baseline_condition!r} and "
            f"{treatment_condition!r}"
        )

    unpaired_baseline = sorted(set(baseline_by_rep) - set(treatment_by_rep))
    unpaired_treatment = sorted(set(treatment_by_rep) - set(baseline_by_rep))

    pair_rows: list[dict[str, Any]] = []
    included_run_ids: list[str] = []
    included_manifest_hashes: dict[str, str] = {}

    for rep in paired_reps:
        b_rate, b_run_id, b_sha = baseline_by_rep[rep]
        t_rate, t_run_id, t_sha = treatment_by_rep[rep]
        included_run_ids.extend([b_run_id, t_run_id])
        included_manifest_hashes[b_run_id] = b_sha
        included_manifest_hashes[t_run_id] = t_sha
        pair_rows.append(
            {
                "replicate_id": rep,
                "target_neuron_id": target_neuron_id,
                "baseline_condition": baseline_condition,
                "treatment_condition": treatment_condition,
                "baseline_rate_hz": b_rate,
                "treatment_rate_hz": t_rate,
                "difference_hz": t_rate - b_rate,
                "baseline_run_id": b_run_id,
                "treatment_run_id": t_run_id,
                "is_synthetic_fixture": bool(provenance_anchor["is_synthetic_fixture"]),
            }
        )

    b_vals = np.array([r["baseline_rate_hz"] for r in pair_rows], dtype=np.float64)
    t_vals = np.array([r["treatment_rate_hz"] for r in pair_rows], dtype=np.float64)
    d_vals = t_vals - b_vals

    b_summary = _summarize_values(b_vals)
    t_summary = _summarize_values(t_vals)

    mean_diff = float(np.mean(d_vals))
    sd_diff = float(np.std(d_vals, ddof=1)) if len(d_vals) > 1 else 0.0
    if len(d_vals) > 1:
        rng = np.random.default_rng(seed_bootstrap)
        boot_idx = rng.integers(0, len(d_vals), size=(n_bootstrap, len(d_vals)))
        boot_means = np.mean(d_vals[boot_idx], axis=1)
        ci95_low = float(np.percentile(boot_means, 2.5))
        ci95_high = float(np.percentile(boot_means, 97.5))
    else:
        ci95_low = mean_diff
        ci95_high = mean_diff

    summary_rows = [
        {
            "condition_id": baseline_condition,
            "target_neuron_id": target_neuron_id,
            **b_summary,
            "is_synthetic_fixture": bool(provenance_anchor["is_synthetic_fixture"]),
        },
        {
            "condition_id": treatment_condition,
            "target_neuron_id": target_neuron_id,
            **t_summary,
            "is_synthetic_fixture": bool(provenance_anchor["is_synthetic_fixture"]),
        },
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_pq = out_dir / "analysis_summary.parquet"
    paired_pq = out_dir / "paired_differences.parquet"
    pl.DataFrame(summary_rows).write_parquet(summary_pq)
    pl.DataFrame(pair_rows).write_parquet(paired_pq)

    paired_metrics = {
        "n_pairs": len(paired_reps),
        "mean_difference_hz": mean_diff,
        "sd_difference_hz": sd_diff,
        "min_difference_hz": float(np.min(d_vals)),
        "max_difference_hz": float(np.max(d_vals)),
        "bootstrap_ci95_low_hz": ci95_low,
        "bootstrap_ci95_high_hz": ci95_high,
        "bootstrap_seed": seed_bootstrap,
        "n_bootstrap": n_bootstrap,
        "permutation_test": paired_permutation_test(d_vals, seed=seed_bootstrap),
        "uncertainty_interpretation": ("conditional_on_model_and_seeds_not_biological_population"),
    }

    manifest_out: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "target_neuron_id": target_neuron_id,
        "baseline_condition": baseline_condition,
        "treatment_condition": treatment_condition,
        "provenance": provenance_anchor,
        "included_run_ids": sorted(included_run_ids),
        "included_run_manifest_sha256s": included_manifest_hashes,
        "unpaired_baseline_replicates": unpaired_baseline,
        "unpaired_treatment_replicates": unpaired_treatment,
        "failed_run_count": len(failed_runs),
        "failed_runs": failed_runs,
        "condition_summaries": {
            baseline_condition: b_summary,
            treatment_condition: t_summary,
        },
        "paired_metrics": paired_metrics,
        "artifacts": {
            "analysis_summary.parquet": sha256_file(summary_pq),
            "paired_differences.parquet": sha256_file(paired_pq),
        },
    }
    manifest_out_path = out_dir / "analysis_manifest.json"
    manifest_out_path.write_text(
        json.dumps(manifest_out, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest_out_path
