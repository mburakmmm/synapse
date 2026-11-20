"""Structurally matched non-target control selection without peeking at neural activity."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from synapse_core.types import DirectedConnectomeGraph


def select_matched_control_neurons(
    graph: DirectedConnectomeGraph,
    target_neuron_ids: Sequence[str],
    *,
    seed: int = 0,
    exclude_neuron_ids: Sequence[str] = (),
    exclude_1hop_downstream_of_targets: bool = True,
    candidate_pool_per_target: int = 100,
) -> dict[str, Any]:
    """Select unique 1-to-1 structurally matched controls matching NT, degrees, and synapse sums."""
    targets = [str(nid) for nid in target_neuron_ids]
    if not targets:
        raise ValueError("target_neuron_ids must be non-empty")
    if len(set(targets)) != len(targets):
        raise ValueError("target_neuron_ids must be unique")
    if candidate_pool_per_target < 1:
        raise ValueError("candidate_pool_per_target must be >= 1")

    target_indices = [graph.index_of(nid) for nid in targets]
    extra_excluded = [graph.index_of(str(nid)) for nid in exclude_neuron_ids]

    pre_idx, post_idx, counts = graph.edge_arrays()
    n_total = graph.n_neurons
    counts_f = counts.astype(np.float64)

    out_deg = np.bincount(pre_idx, minlength=n_total).astype(np.float64)
    in_deg = np.bincount(post_idx, minlength=n_total).astype(np.float64)
    out_syn = np.bincount(pre_idx, weights=counts_f, minlength=n_total).astype(np.float64)
    in_syn = np.bincount(post_idx, weights=counts_f, minlength=n_total).astype(np.float64)

    eligible = np.ones(n_total, dtype=bool)
    eligible[target_indices] = False
    if extra_excluded:
        eligible[extra_excluded] = False
    if exclude_1hop_downstream_of_targets and len(pre_idx) > 0:
        is_target_pre = np.isin(pre_idx, target_indices)
        downstream_indices = post_idx[is_target_pre]
        if len(downstream_indices) > 0:
            eligible[downstream_indices] = False

    # Standardized log1p structural feature space (strictly static graph properties)
    raw_features = {
        "out_degree": out_deg,
        "out_synapses": out_syn,
        "in_degree": in_deg,
        "in_synapses": in_syn,
    }
    feat_matrix = np.column_stack([np.log1p(v) for v in raw_features.values()])
    ref_mask = eligible.copy()
    ref_mask[target_indices] = True
    mean_vec = np.mean(feat_matrix[ref_mask], axis=0)
    sd_vec = np.std(feat_matrix[ref_mask], axis=0)
    sd_safe = np.where(sd_vec > 1e-9, sd_vec, 1.0)
    z_feat = (feat_matrix - mean_vec) / sd_safe

    # Group targets by exact neurotransmitter label so controls preserve phenotype category
    by_nt: dict[str | None, list[int]] = defaultdict(list)
    for pos, t_idx in enumerate(target_indices):
        by_nt[graph.neurotransmitters[t_idx]].append(pos)

    nt_array = np.array(graph.neurotransmitters, dtype=object)
    rng = np.random.default_rng(seed)
    matched_control_idx = [-1] * len(targets)

    for nt_label, target_positions in by_nt.items():
        if nt_label is None:
            cand_mask = eligible & np.array([val is None for val in nt_array], dtype=bool)
        else:
            cand_mask = eligible & (nt_array == nt_label)
        cand_indices = np.flatnonzero(cand_mask)
        k_group = len(target_positions)
        if len(cand_indices) < k_group:
            raise ValueError(
                f"Insufficient eligible structurally matched controls for NT={nt_label!r}: "
                f"need {k_group}, found {len(cand_indices)}"
            )

        t_idx_group = np.array([target_indices[p] for p in target_positions], dtype=np.int64)
        pool_k = min(len(cand_indices), max(candidate_pool_per_target, k_group * 2))
        pooled_pos: set[int] = set()
        cand_feats = z_feat[cand_indices]
        for t_idx in t_idx_group:
            diffs = cand_feats - z_feat[t_idx]
            dists = np.sum(diffs * diffs, axis=1)
            if pool_k < len(cand_indices):
                nearest_local = np.argpartition(dists, pool_k - 1)[:pool_k]
            else:
                nearest_local = np.arange(len(cand_indices), dtype=np.int64)
            pooled_pos.update(int(cand_indices[loc]) for loc in nearest_local)

        pool_arr = np.array(sorted(pooled_pos), dtype=np.int64)
        t_mat = z_feat[t_idx_group][:, None, :]
        c_mat = z_feat[pool_arr][None, :, :]
        cost = np.sum((t_mat - c_mat) ** 2, axis=2)
        # Seeded tiny tie-breaker strictly smaller than real feature differences
        cost = cost + rng.uniform(0.0, 1e-10, size=cost.shape)
        row_ind, col_ind = linear_sum_assignment(cost)
        for r_i, c_j in zip(row_ind.tolist(), col_ind.tolist(), strict=True):
            chosen_idx = int(pool_arr[c_j])
            matched_control_idx[target_positions[r_i]] = chosen_idx
            eligible[chosen_idx] = False

    assert all(idx >= 0 for idx in matched_control_idx)
    control_ids = [graph.neuron_ids[idx] for idx in matched_control_idx]

    pair_matches: list[dict[str, Any]] = []
    for t_nid, t_idx, c_nid, c_idx in zip(
        targets, target_indices, control_ids, matched_control_idx, strict=True
    ):
        pair_matches.append(
            {
                "target_neuron_id": t_nid,
                "control_neuron_id": c_nid,
                "neurotransmitter": graph.neurotransmitters[t_idx],
                "target_out_degree": int(out_deg[t_idx]),
                "control_out_degree": int(out_deg[c_idx]),
                "target_out_synapses": int(out_syn[t_idx]),
                "control_out_synapses": int(out_syn[c_idx]),
                "target_in_degree": int(in_deg[t_idx]),
                "control_in_degree": int(in_deg[c_idx]),
                "target_in_synapses": int(in_syn[t_idx]),
                "control_in_synapses": int(in_syn[c_idx]),
            }
        )

    residual_imbalance: dict[str, dict[str, float]] = {}
    t_idx_arr = np.array(target_indices, dtype=np.int64)
    c_idx_arr = np.array(matched_control_idx, dtype=np.int64)
    ddof = 1 if len(targets) > 1 else 0
    for feat_name, vec in raw_features.items():
        t_vals = vec[t_idx_arr]
        c_vals = vec[c_idx_arr]
        t_mean = float(np.mean(t_vals))
        c_mean = float(np.mean(c_vals))
        t_sd = float(np.std(t_vals, ddof=ddof))
        c_sd = float(np.std(c_vals, ddof=ddof))
        pooled_sd = float(np.sqrt(0.5 * (t_sd * t_sd + c_sd * c_sd)))
        smd = 0.0 if pooled_sd == 0.0 else (c_mean - t_mean) / pooled_sd
        rel_diff = abs(c_mean - t_mean) / max(abs(t_mean), 1.0)
        residual_imbalance[feat_name] = {
            "target_mean": t_mean,
            "control_mean": c_mean,
            "target_sd": t_sd,
            "control_sd": c_sd,
            "smd": smd,
            "abs_rel_mean_diff": rel_diff,
        }

    return {
        "schema_version": "1.0",
        "source_dataset_id": graph.dataset_id,
        "source_release": graph.release,
        "source_specimen_id": graph.specimen_id,
        "source_graph_sha256": graph.graph_sha256(),
        "seed": seed,
        "exclude_1hop_downstream_of_targets": exclude_1hop_downstream_of_targets,
        "excluded_neuron_count": int(n_total - np.count_nonzero(eligible) - len(targets)),
        "matching_features": list(raw_features),
        "target_neuron_ids": targets,
        "control_neuron_ids": control_ids,
        "pair_matches": pair_matches,
        "residual_imbalance": residual_imbalance,
    }
