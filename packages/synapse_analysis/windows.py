"""Windowed pre-, stimulus-, and post-stimulus firing and persistence summaries."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


def _validate_window(name: str, bounds: tuple[float, float]) -> tuple[float, float]:
    if len(bounds) != 2:
        raise ValueError(f"{name} must be a (start_s, end_s) pair")
    start_s, end_s = float(bounds[0]), float(bounds[1])
    if not (math.isfinite(start_s) and math.isfinite(end_s)):
        raise ValueError(f"{name} bounds must be finite, got {bounds!r}")
    if start_s < 0.0 or end_s <= start_s:
        raise ValueError(f"{name} requires 0 <= start_s < end_s, got {bounds!r}")
    return start_s, end_s


def _summarize_numeric(values: Sequence[float]) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=np.float64)
    n = int(arr.size)
    if n == 0:
        return {
            "n_seed_replicates": 0,
            "mean": 0.0,
            "sd": 0.0,
            "median": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "iqr": 0.0,
        }
    q25 = float(np.percentile(arr, 25))
    med = float(np.percentile(arr, 50))
    q75 = float(np.percentile(arr, 75))
    return {
        "n_seed_replicates": n,
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)) if n > 1 else 0.0,
        "median": med,
        "q25": q25,
        "q75": q75,
        "iqr": q75 - q25,
    }


def _window_stats(
    times: np.ndarray,
    *,
    pre_w: tuple[float, float],
    stim_w: tuple[float, float],
    post_w: tuple[float, float],
) -> dict[str, float | int]:
    pre_dur = pre_w[1] - pre_w[0]
    stim_dur = stim_w[1] - stim_w[0]
    post_dur = post_w[1] - post_w[0]

    if times.size == 0:
        return {
            "pre_rate_hz": 0.0,
            "stim_rate_hz": 0.0,
            "post_rate_hz": 0.0,
            "post_spike_count": 0,
            "persistence_duration_s": 0.0,
        }

    pre_cnt = int(np.count_nonzero((times >= pre_w[0]) & (times < pre_w[1])))
    stim_cnt = int(np.count_nonzero((times >= stim_w[0]) & (times < stim_w[1])))
    post_mask = (times >= post_w[0]) & (times <= post_w[1])
    post_cnt = int(np.count_nonzero(post_mask))
    persistence_s = float(np.max(times[post_mask]) - post_w[0]) if post_cnt > 0 else 0.0
    return {
        "pre_rate_hz": pre_cnt / pre_dur,
        "stim_rate_hz": stim_cnt / stim_dur,
        "post_rate_hz": post_cnt / post_dur,
        "post_spike_count": post_cnt,
        "persistence_duration_s": persistence_s,
    }


def compute_windowed_response_metrics(
    runs_dir: Path,
    *,
    neuron_ids: Sequence[str],
    pre_window: tuple[float, float],
    stim_window: tuple[float, float],
    post_window: tuple[float, float],
    condition_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compute per-window firing rates and post-stimulus persistence from run spike artifacts."""
    if not runs_dir.is_dir():
        raise ValueError(f"runs_dir does not exist: {runs_dir}")

    target_ids = tuple(dict.fromkeys(str(nid) for nid in neuron_ids))
    if not target_ids or any(not nid for nid in target_ids):
        raise ValueError("neuron_ids must contain at least one non-empty neuron ID")

    pre_w = _validate_window("pre_window", pre_window)
    stim_w = _validate_window("stim_window", stim_window)
    post_w = _validate_window("post_window", post_window)
    cond_filter = None if condition_ids is None else set(str(c) for c in condition_ids)

    succeeded_runs: list[tuple[Path, dict[str, Any]]] = []
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

        if cond_filter is not None and str(manifest["condition_id"]) not in cond_filter:
            continue
        succeeded_runs.append((candidate, manifest))

    if not succeeded_runs:
        raise ValueError(f"No matching succeeded runs found under {runs_dir}")

    per_replicate_rows: list[dict[str, Any]] = []
    cond_agg_metrics: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    cond_neuron_metrics: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    target_list = list(target_ids)
    for run_dir, manifest in succeeded_runs:
        spikes_path = run_dir / "spikes.parquet"
        if not spikes_path.is_file():
            raise ValueError(f"Missing spikes.parquet in succeeded run: {run_dir}")

        spk_df = (
            pl.scan_parquet(spikes_path)
            .filter(pl.col("source_neuron_id").is_in(target_list))
            .select(["source_neuron_id", "spike_time_s"])
            .collect()
        )

        cond_id = str(manifest["condition_id"])
        rep_id = int(manifest["replicate_id"])
        run_id = str(manifest["run_id"])

        by_nid: dict[str, list[float]] = {nid: [] for nid in target_ids}
        for row_nid, row_t in spk_df.iter_rows():
            by_nid[str(row_nid)].append(float(row_t))

        neuron_stats: dict[str, dict[str, float | int]] = {}
        for nid in target_ids:
            times = np.asarray(by_nid[nid], dtype=np.float64)
            stats = _window_stats(times, pre_w=pre_w, stim_w=stim_w, post_w=post_w)
            neuron_stats[nid] = stats
            for metric_name in (
                "pre_rate_hz",
                "stim_rate_hz",
                "post_rate_hz",
                "persistence_duration_s",
            ):
                cond_neuron_metrics[(cond_id, nid)][metric_name].append(float(stats[metric_name]))

        agg_pre = float(np.mean([neuron_stats[n]["pre_rate_hz"] for n in target_ids]))
        agg_stim = float(np.mean([neuron_stats[n]["stim_rate_hz"] for n in target_ids]))
        agg_post = float(np.mean([neuron_stats[n]["post_rate_hz"] for n in target_ids]))
        agg_post_cnt = int(sum(int(neuron_stats[n]["post_spike_count"]) for n in target_ids))
        agg_persist = float(
            max(float(neuron_stats[n]["persistence_duration_s"]) for n in target_ids)
        )

        for metric_name, val in (
            ("pre_rate_hz", agg_pre),
            ("stim_rate_hz", agg_stim),
            ("post_rate_hz", agg_post),
            ("persistence_duration_s", agg_persist),
        ):
            cond_agg_metrics[cond_id][metric_name].append(val)

        per_replicate_rows.append(
            {
                "run_id": run_id,
                "condition_id": cond_id,
                "replicate_id": rep_id,
                "pre_rate_hz": agg_pre,
                "stim_rate_hz": agg_stim,
                "post_rate_hz": agg_post,
                "post_spike_count": agg_post_cnt,
                "persistence_duration_s": agg_persist,
                "per_neuron": neuron_stats,
            }
        )

    per_replicate_rows.sort(key=lambda r: (str(r["condition_id"]), int(r["replicate_id"])))

    condition_summaries: dict[str, dict[str, Any]] = {}
    for cond_id in sorted(cond_agg_metrics):
        condition_summaries[cond_id] = {
            metric_name: _summarize_numeric(vals)
            for metric_name, vals in cond_agg_metrics[cond_id].items()
        }

    per_neuron_condition_summaries: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for (cond_id, nid), metric_map in sorted(cond_neuron_metrics.items()):
        per_neuron_condition_summaries[cond_id][nid] = {
            metric_name: _summarize_numeric(vals) for metric_name, vals in metric_map.items()
        }

    return {
        "windows": {
            "pre_window_s": list(pre_w),
            "stim_window_s": list(stim_w),
            "post_window_s": list(post_w),
        },
        "neuron_ids": list(target_ids),
        "succeeded_run_count": len(succeeded_runs),
        "failed_run_count": len(failed_runs),
        "failed_runs": failed_runs,
        "condition_summaries": condition_summaries,
        "per_neuron_condition_summaries": dict(per_neuron_condition_summaries),
        "per_replicate_rows": per_replicate_rows,
    }
