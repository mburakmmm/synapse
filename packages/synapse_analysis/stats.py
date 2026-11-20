"""Statistical permutation inference, FDR control, and local sensitivity summaries."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


def paired_permutation_test(
    differences: np.ndarray | Sequence[float],
    *,
    seed: int = 0,
    n_permutations: int = 10000,
    exact_threshold: int = 14,
) -> dict[str, Any]:
    """Two-sided paired sign-flip permutation test conditional on model and seed ensemble."""
    arr = np.asarray(differences, dtype=np.float64)
    if arr.ndim != 1 or len(arr) < 1:
        raise ValueError("differences must be a non-empty 1D sequence")
    if not np.all(np.isfinite(arr)):
        raise ValueError("differences must contain only finite values")
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    if exact_threshold < 1:
        raise ValueError("exact_threshold must be >= 1")

    n = len(arr)
    obs_mean = float(np.mean(arr))
    assumption = "paired_simulation_seeds_under_fixed_connectome_and_model"
    if np.all(arr == 0.0):
        return {
            "method": "deterministic_zero_difference",
            "n_pairs": n,
            "observed_mean_diff_hz": 0.0,
            "two_sided_p_value": 1.0,
            "n_evaluations": 1,
            "seed": None,
            "deterministic_zero_variance": True,
            "exchangeability_assumption": assumption,
        }

    abs_obs = abs(obs_mean)
    tol = 1e-12
    zero_var = bool(np.std(arr) == 0.0)

    if n <= exact_threshold:
        patterns = np.arange(1 << n, dtype=np.uint32)[:, None]
        bit_idx = np.arange(n, dtype=np.uint32)[None, :]
        signs = ((patterns >> bit_idx) & 1).astype(np.float64) * 2.0 - 1.0
        perm_means = (signs @ arr) / float(n)
        n_eval = 1 << n
        n_extreme = int(np.count_nonzero(np.abs(perm_means) >= abs_obs - tol))
        p_val = float(n_extreme / n_eval)
        return {
            "method": "exact_sign_flip",
            "n_pairs": n,
            "observed_mean_diff_hz": obs_mean,
            "two_sided_p_value": p_val,
            "n_evaluations": n_eval,
            "seed": None,
            "deterministic_zero_variance": zero_var,
            "exchangeability_assumption": assumption,
        }

    rng = np.random.default_rng(seed)
    chunk_size = 2000
    n_extreme = 0
    remaining = n_permutations
    while remaining > 0:
        cur = min(chunk_size, remaining)
        signs = rng.choice((-1.0, 1.0), size=(cur, n))
        perm_means = (signs @ arr) / float(n)
        n_extreme += int(np.count_nonzero(np.abs(perm_means) >= abs_obs - tol))
        remaining -= cur

    # +1 Laplace/Phipson-Smyth adjustment preserves valid Monte Carlo Type I bound
    p_val = float((n_extreme + 1) / (n_permutations + 1))
    return {
        "method": "monte_carlo_sign_flip",
        "n_pairs": n,
        "observed_mean_diff_hz": obs_mean,
        "two_sided_p_value": p_val,
        "n_evaluations": n_permutations,
        "seed": seed,
        "deterministic_zero_variance": zero_var,
        "exchangeability_assumption": "paired_simulation_seeds_under_fixed_connectome_and_model",
    }


def bh_fdr_adjust(p_values: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg step-up FDR q-values for a family of p-values in [0, 1]."""
    if len(p_values) == 0:
        return []
    arr = np.asarray(p_values, dtype=np.float64)
    if arr.ndim != 1 or not np.all(np.isfinite(arr)):
        raise ValueError("p_values must be finite")
    if np.any((arr < 0.0) | (arr > 1.0)):
        raise ValueError("All p_values must lie within [0.0, 1.0]")

    m = len(arr)
    order = np.argsort(arr, kind="mergesort")
    ranked = arr[order]
    ranks = np.arange(1, m + 1, dtype=np.float64)
    adjusted_sorted = (ranked * float(m)) / ranks
    adjusted_sorted = np.minimum.accumulate(adjusted_sorted[::-1])[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)

    out = np.empty(m, dtype=np.float64)
    out[order] = adjusted_sorted
    return [float(x) for x in out]


def local_sensitivity_summary(
    parameter_name: str,
    grid_values: Sequence[float],
    endpoint_values: Sequence[float],
    *,
    baseline_value: float,
) -> dict[str, Any]:
    """Summarize endpoint sensitivity range and monotonicity over a 1D parameter grid."""
    if not parameter_name.strip():
        raise ValueError("parameter_name must be non-empty")
    if len(grid_values) < 2 or len(grid_values) != len(endpoint_values):
        raise ValueError("grid_values and endpoint_values must share length >= 2")

    g = np.asarray(grid_values, dtype=np.float64)
    y = np.asarray(endpoint_values, dtype=np.float64)
    if not (np.all(np.isfinite(g)) and np.all(np.isfinite(y)) and np.isfinite(baseline_value)):
        raise ValueError("Sensitivity inputs must be finite")

    order = np.argsort(g, kind="mergesort")
    g_sorted = g[order]
    y_sorted = y[order]

    diffs = np.diff(y_sorted)
    tol = 1e-12
    if np.all(np.abs(diffs) <= tol):
        trend = "constant"
    elif np.all(diffs >= -tol):
        trend = "monotone_increasing"
    elif np.all(diffs <= tol):
        trend = "monotone_decreasing"
    else:
        trend = "non_monotone"

    base_idx = int(np.argmin(np.abs(g_sorted - baseline_value)))
    baseline_endpoint = float(y_sorted[base_idx])
    min_y = float(np.min(y_sorted))
    max_y = float(np.max(y_sorted))
    return {
        "parameter_name": parameter_name,
        "n_points": len(g_sorted),
        "grid_min": float(g_sorted[0]),
        "grid_max": float(g_sorted[-1]),
        "baseline_grid_value": float(g_sorted[base_idx]),
        "baseline_endpoint_value": baseline_endpoint,
        "endpoint_min": min_y,
        "endpoint_max": max_y,
        "endpoint_range": max_y - min_y,
        "max_abs_shift_from_baseline": float(np.max(np.abs(y_sorted - baseline_endpoint))),
        "trend": trend,
    }
