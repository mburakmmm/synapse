"""L0 connectome topology, fragmentation, and exact cell/synapse ablation audit engine (RUO)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, shortest_path

from synapse_core.types import DEFAULT_SIGN_MAP, DirectedConnectomeGraph, DirectedEdge

_NEURO_SOURCE = (
    "Albert et al. Nature 2000 (10.1038/35019019); "
    "Latora & Marchiori PRL 2001 (10.1103/PhysRevLett.87.198701); "
    "Rubinov & Sporns NeuroImage 2010 (10.1016/j.neuroimage.2009.10.003); "
    "Lin et al. Nature 2024 (10.1038/s41586-024-07968-y)"
)


class TopologyAnalysisParameters(BaseModel):
    """Explicit L0 graph topology & ablation audit configuration (Research Use Only)."""

    model_config = ConfigDict(frozen=True)

    model_id: str = "neuro_topology_ablation_v1"
    model_revision: str = "1.0"
    model_level: Literal["L0"] = "L0"
    min_synapse_threshold: int = 1
    excitatory_only_pathway: bool = True
    distance_weighting: Literal["inverse_synapse_count"] = "inverse_synapse_count"
    parameter_source: str = _NEURO_SOURCE

    @model_validator(mode="after")
    def _validate_bounds(self) -> TopologyAnalysisParameters:
        if isinstance(self.min_synapse_threshold, bool) or self.min_synapse_threshold < 1:
            raise ValueError(
                f"min_synapse_threshold must be an integer >= 1, got {self.min_synapse_threshold}"
            )
        return self

    def canonical_sha256(self) -> str:
        """Compute canonical SHA-256 digest of L0 topology parameters."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AblationAuditRecord(BaseModel):
    """Exact immutable provenance record of every node and edge modified by an ablation."""

    model_config = ConfigDict(frozen=True)

    ablation_id: str
    ablation_kind: Literal["none", "node_ablation", "edge_mask_ablation"]
    removed_neuron_ids: tuple[str, ...]
    removed_node_count: int
    removed_edge_count: int
    removed_synapse_count: float
    removed_synapse_fraction: float
    removed_edges_sha256: str
    removed_edges_sample: tuple[dict[str, Any], ...]
    ablation_manifest_sha256: str


class TopologyIntegrityMetrics(BaseModel):
    """Whole-graph fragmentation and directional pathway efficiency metrics on surviving nodes."""

    model_config = ConfigDict(frozen=True)

    n_total_nodes: int
    n_active_nodes: int
    n_active_edges: int
    total_active_synapses: float
    wcc_count: int
    largest_wcc_nodes: int
    largest_wcc_fraction: float
    scc_count: int
    largest_scc_nodes: int
    largest_scc_fraction: float
    source_target_pair_count: int
    reachable_pair_count: int
    reachability_fraction: float
    unweighted_harmonic_efficiency: float
    weighted_pathway_efficiency: float
    mean_shortest_hop_distance: float | None
    two_hop_exc_flow: float
    three_hop_exc_flow: float
    target_exc_in_synapses: float


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compute_shortest_paths(
    *,
    cost_weights: np.ndarray,
    pre_vertices: np.ndarray,
    post_vertices: np.ndarray,
    n_neurons: int,
    src_idx: np.ndarray,
    tgt_idx: np.ndarray,
    unweighted: bool,
) -> np.ndarray:
    """Compute directional shortest-path matrix [n_src, n_tgt] picking faster traversal side."""
    if len(cost_weights) == 0:
        return np.full((len(src_idx), len(tgt_idx)), np.inf, dtype=np.float64)
    if len(tgt_idx) < len(src_idx):
        # Reverse graph (row=post, col=pre) starting from smaller target set is ~10x faster.
        mat_rev = csr_matrix(
            (cost_weights, (post_vertices, pre_vertices)), shape=(n_neurons, n_neurons)
        )
        dist_rev = shortest_path(
            mat_rev,
            directed=True,
            indices=tgt_idx,
            unweighted=unweighted,
        )
        dist_rev = np.atleast_2d(dist_rev)
        return np.asarray(dist_rev[:, src_idx].T, dtype=np.float64)

    mat_fwd = csr_matrix(
        (cost_weights, (pre_vertices, post_vertices)), shape=(n_neurons, n_neurons)
    )
    dist_fwd = shortest_path(
        mat_fwd,
        directed=True,
        indices=src_idx,
        unweighted=unweighted,
    )
    dist_fwd = np.atleast_2d(dist_fwd)
    return np.asarray(dist_fwd[:, tgt_idx], dtype=np.float64)


def evaluate_graph_ablation(
    graph: DirectedConnectomeGraph,
    *,
    source_neuron_ids: Sequence[str],
    target_neuron_ids: Sequence[str],
    params: TopologyAnalysisParameters | None = None,
    ablation_id: str = "baseline",
    removed_neuron_ids: Sequence[str] = (),
    edge_mask_pre_ids: Sequence[str] = (),
    edge_mask_post_ids: Sequence[str] = (),
    edge_mask_factor: float = 1.0,
    max_edge_sample: int = 200,
) -> dict[str, Any]:
    """Evaluate L0 whole-graph fragmentation and directional efficiency non-destructively."""
    cfg = params or TopologyAnalysisParameters()
    if not source_neuron_ids or not target_neuron_ids:
        raise ValueError("source_neuron_ids and target_neuron_ids must both be non-empty")
    if not math.isfinite(edge_mask_factor) or edge_mask_factor < 0.0 or edge_mask_factor > 1.0:
        raise ValueError(f"edge_mask_factor must be finite in [0.0, 1.0], got {edge_mask_factor}")

    unique_src = tuple(dict.fromkeys(str(x) for x in source_neuron_ids))
    unique_tgt = tuple(dict.fromkeys(str(x) for x in target_neuron_ids))
    src_idx = np.array([graph.index_of(nid) for nid in unique_src], dtype=np.int64)
    tgt_idx = np.array([graph.index_of(nid) for nid in unique_tgt], dtype=np.int64)

    unique_rem_nodes = tuple(sorted({str(x) for x in removed_neuron_ids}))
    rem_node_indices = [graph.index_of(nid) for nid in unique_rem_nodes]

    has_edge_mask = bool(edge_mask_pre_ids or edge_mask_post_ids)
    if has_edge_mask and (not edge_mask_pre_ids or not edge_mask_post_ids):
        raise ValueError("Both edge_mask_pre_ids and edge_mask_post_ids must be provided together")
    if unique_rem_nodes and has_edge_mask:
        raise ValueError(
            "Provide either removed_neuron_ids or edge_mask_* per evaluation, not both"
        )

    pre_idx, post_idx, raw_counts = graph.edge_arrays()
    counts_f = raw_counts.astype(np.float64)
    n_total = graph.n_neurons
    total_raw_synapses = float(counts_f.sum())

    if unique_rem_nodes:
        ablation_kind: Literal["none", "node_ablation", "edge_mask_ablation"] = "node_ablation"
        rem_set = np.array(rem_node_indices, dtype=np.int64)
        active_mask = np.ones(n_total, dtype=bool)
        active_mask[rem_set] = False
        affected_edge_mask = (~active_mask[pre_idx]) | (~active_mask[post_idx])
        lost_synapses_vec = np.where(affected_edge_mask, counts_f, 0.0)
        eff_weights = np.where(affected_edge_mask, 0.0, counts_f)
    elif has_edge_mask and edge_mask_factor < 1.0:
        ablation_kind = "edge_mask_ablation"
        active_mask = np.ones(n_total, dtype=bool)
        pre_mask_idx = np.array(
            [graph.index_of(str(nid)) for nid in edge_mask_pre_ids], dtype=np.int64
        )
        post_mask_idx = np.array(
            [graph.index_of(str(nid)) for nid in edge_mask_post_ids], dtype=np.int64
        )
        affected_edge_mask = np.isin(pre_idx, pre_mask_idx) & np.isin(post_idx, post_mask_idx)
        lost_synapses_vec = np.where(
            affected_edge_mask,
            counts_f * (1.0 - edge_mask_factor),
            0.0,
        )
        eff_weights = np.where(affected_edge_mask, counts_f * edge_mask_factor, counts_f)
    else:
        ablation_kind = "none"
        active_mask = np.ones(n_total, dtype=bool)
        affected_edge_mask = np.zeros(len(counts_f), dtype=bool)
        lost_synapses_vec = np.zeros(len(counts_f), dtype=np.float64)
        eff_weights = counts_f.copy()

    # Exact audit of every removed/attenuated edge
    aff_positions = np.flatnonzero(affected_edge_mask)
    removed_edge_entries: list[tuple[str, str, float, int]] = []
    for pos in aff_positions.tolist():
        lost_val = float(lost_synapses_vec[pos])
        if lost_val > 0.0:
            removed_edge_entries.append(
                (
                    graph.neuron_ids[int(pre_idx[pos])],
                    graph.neuron_ids[int(post_idx[pos])],
                    lost_val,
                    int(raw_counts[pos]),
                )
            )
    removed_edge_entries.sort(key=lambda r: (r[0], r[1]))
    removed_edges_sha256 = _sha256_json(
        [(pre_s, post_s, round(lost_s, 9)) for pre_s, post_s, lost_s, _ in removed_edge_entries]
    )
    ranked_sample = sorted(removed_edge_entries, key=lambda r: (-r[2], r[0], r[1]))[
        :max_edge_sample
    ]
    sample_dicts = tuple(
        {
            "pre_neuron_id": pre_s,
            "post_neuron_id": post_s,
            "original_synapses": orig_s,
            "lost_synapses": round(lost_s, 6),
        }
        for pre_s, post_s, lost_s, orig_s in ranked_sample
    )
    removed_syn_total = float(sum(r[2] for r in removed_edge_entries))
    removed_syn_frac = removed_syn_total / total_raw_synapses if total_raw_synapses > 0.0 else 0.0

    manifest_payload = {
        "ablation_id": ablation_id,
        "ablation_kind": ablation_kind,
        "source_graph_sha256": graph.graph_sha256(),
        "removed_neuron_ids": list(unique_rem_nodes),
        "edge_mask_factor": edge_mask_factor,
        "removed_edge_count": len(removed_edge_entries),
        "removed_synapse_count": round(removed_syn_total, 9),
        "removed_edges_sha256": removed_edges_sha256,
    }
    audit = AblationAuditRecord(
        ablation_id=ablation_id,
        ablation_kind=ablation_kind,
        removed_neuron_ids=unique_rem_nodes,
        removed_node_count=len(unique_rem_nodes),
        removed_edge_count=len(removed_edge_entries),
        removed_synapse_count=round(removed_syn_total, 6),
        removed_synapse_fraction=removed_syn_frac,
        removed_edges_sha256=removed_edges_sha256,
        removed_edges_sample=sample_dicts,
        ablation_manifest_sha256=_sha256_json(manifest_payload),
    )

    # Whole-network integrity on surviving active nodes
    thresh = float(cfg.min_synapse_threshold)
    surviving_edge_mask = (eff_weights >= thresh) & (eff_weights > 0.0)
    active_indices = np.flatnonzero(active_mask)
    n_active_nodes = len(active_indices)
    n_active_edges = int(np.count_nonzero(surviving_edge_mask))
    total_active_syn = float(eff_weights[surviving_edge_mask].sum())

    if n_active_nodes == 0:
        wcc_count = 0
        largest_wcc = 0
        scc_count = 0
        largest_scc = 0
    else:
        old_to_active = np.full(n_total, -1, dtype=np.int64)
        old_to_active[active_indices] = np.arange(n_active_nodes, dtype=np.int64)
        a_pre = old_to_active[pre_idx[surviving_edge_mask]]
        a_post = old_to_active[post_idx[surviving_edge_mask]]
        w_active = csr_matrix(
            (eff_weights[surviving_edge_mask], (a_post, a_pre)),
            shape=(n_active_nodes, n_active_nodes),
        )
        wcc_count, wcc_labels = connected_components(w_active, directed=False, return_labels=True)
        largest_wcc = int(np.bincount(wcc_labels).max()) if n_active_nodes > 0 else 0
        scc_count, scc_labels = connected_components(
            w_active, directed=True, connection="strong", return_labels=True
        )
        largest_scc = int(np.bincount(scc_labels).max()) if n_active_nodes > 0 else 0

    # Directional source -> target efficiency and multi-hop flow
    if cfg.excitatory_only_pathway:
        is_exc = np.array(
            [DEFAULT_SIGN_MAP.get(nt or "", 0.0) > 0.0 for nt in graph.neurotransmitters],
            dtype=bool,
        )
        pathway_mask = surviving_edge_mask & is_exc[pre_idx]
    else:
        pathway_mask = surviving_edge_mask

    p_pre = pre_idx[pathway_mask]
    p_post = post_idx[pathway_mask]
    p_weights = eff_weights[pathway_mask]
    p_costs = 1.0 / p_weights

    dist_u = _compute_shortest_paths(
        cost_weights=p_costs,
        pre_vertices=p_pre,
        post_vertices=p_post,
        n_neurons=n_total,
        src_idx=src_idx,
        tgt_idx=tgt_idx,
        unweighted=True,
    )
    dist_w = _compute_shortest_paths(
        cost_weights=p_costs,
        pre_vertices=p_pre,
        post_vertices=p_post,
        n_neurons=n_total,
        src_idx=src_idx,
        tgt_idx=tgt_idx,
        unweighted=False,
    )

    pair_count = int(len(src_idx) * len(tgt_idx))
    finite_u = np.isfinite(dist_u)
    reachable_count = int(np.count_nonzero(finite_u))
    reachability_frac = reachable_count / pair_count if pair_count > 0 else 0.0
    inv_u = np.where(finite_u & (dist_u > 0.0), 1.0 / dist_u, 0.0)
    inv_w = np.where(np.isfinite(dist_w) & (dist_w > 0.0), 1.0 / dist_w, 0.0)
    mean_hops = float(np.mean(dist_u[finite_u])) if reachable_count > 0 else None

    # 2-hop and 3-hop pathway throughput W_path @ ... @ s0 where W_path[post, pre] = eff_weight
    w_path = csr_matrix((p_weights, (p_post, p_pre)), shape=(n_total, n_total))
    s0 = np.zeros(n_total, dtype=np.float64)
    s0[src_idx] = 1.0
    hop1 = w_path @ s0
    hop2 = w_path @ hop1
    hop3 = w_path @ hop2
    two_hop_flow = float(hop2[tgt_idx].sum())
    three_hop_flow = float(hop3[tgt_idx].sum())
    target_in_syn = float(w_path[tgt_idx, :].sum())

    metrics = TopologyIntegrityMetrics(
        n_total_nodes=n_total,
        n_active_nodes=n_active_nodes,
        n_active_edges=n_active_edges,
        total_active_synapses=round(total_active_syn, 6),
        wcc_count=int(wcc_count),
        largest_wcc_nodes=largest_wcc,
        largest_wcc_fraction=largest_wcc / n_total if n_total > 0 else 0.0,
        scc_count=int(scc_count),
        largest_scc_nodes=largest_scc,
        largest_scc_fraction=largest_scc / n_total if n_total > 0 else 0.0,
        source_target_pair_count=pair_count,
        reachable_pair_count=reachable_count,
        reachability_fraction=reachability_frac,
        unweighted_harmonic_efficiency=float(np.mean(inv_u)) if pair_count > 0 else 0.0,
        weighted_pathway_efficiency=float(np.mean(inv_w)) if pair_count > 0 else 0.0,
        mean_shortest_hop_distance=mean_hops,
        two_hop_exc_flow=round(two_hop_flow, 6),
        three_hop_exc_flow=round(three_hop_flow, 6),
        target_exc_in_synapses=round(target_in_syn, 6),
    )

    return {
        "ablation_id": ablation_id,
        "audit": audit.model_dump(mode="json"),
        "metrics": metrics.model_dump(mode="json"),
    }


def _enrich_curve_point(
    arm_type: str,
    step_k: int,
    raw: dict[str, Any],
    base_metrics: dict[str, Any],
) -> dict[str, Any]:
    m = raw["metrics"]
    a = raw["audit"]
    w_eff_base = float(base_metrics["weighted_pathway_efficiency"])
    flow3_base = float(base_metrics["three_hop_exc_flow"])
    tgt_syn_base = float(base_metrics["target_exc_in_synapses"])
    return {
        "arm_type": arm_type,
        "step_k": step_k,
        "ablation_id": raw["ablation_id"],
        "weighted_eff_ratio": (
            float(m["weighted_pathway_efficiency"]) / w_eff_base if w_eff_base > 0.0 else 0.0
        ),
        "three_hop_flow_ratio": (
            float(m["three_hop_exc_flow"]) / flow3_base if flow3_base > 0.0 else 0.0
        ),
        "target_exc_syn_retention": (
            float(m["target_exc_in_synapses"]) / tgt_syn_base if tgt_syn_base > 0.0 else 0.0
        ),
        "removed_node_count": a["removed_node_count"],
        "removed_edge_count": a["removed_edge_count"],
        "removed_synapse_count": a["removed_synapse_count"],
        "audit": a,
        "metrics": m,
    }


def run_progressive_ablation_curve(
    graph: DirectedConnectomeGraph,
    *,
    source_neuron_ids: Sequence[str],
    target_neuron_ids: Sequence[str],
    targeted_hub_ids: Sequence[str],
    matched_control_ids: Sequence[str],
    ctrl_syn_pre_ids: Sequence[str] = (),
    ctrl_syn_post_ids: Sequence[str] = (),
    params: TopologyAnalysisParameters | None = None,
    step_counts: Sequence[int] = (0, 2, 4, 6, 8, 10, 12),
) -> dict[str, Any]:
    """Evaluate progressive targeted vs matched-random node and synapse loss curves."""
    cfg = params or TopologyAnalysisParameters()
    if len(targeted_hub_ids) != len(matched_control_ids):
        raise ValueError("targeted_hub_ids and matched_control_ids must have equal length")

    baseline_raw = evaluate_graph_ablation(
        graph,
        source_neuron_ids=source_neuron_ids,
        target_neuron_ids=target_neuron_ids,
        params=cfg,
        ablation_id="intact_baseline",
    )
    base_m = baseline_raw["metrics"]

    valid_steps = tuple(sorted({k for k in step_counts if 0 <= k <= len(targeted_hub_ids)}))
    if 0 not in valid_steps:
        valid_steps = (0, *valid_steps)

    curve_points: list[dict[str, Any]] = []
    for k in valid_steps:
        if k == 0:
            curve_points.append(_enrich_curve_point("targeted_cell_loss", 0, baseline_raw, base_m))
            curve_points.append(
                _enrich_curve_point("matched_random_cell_loss", 0, baseline_raw, base_m)
            )
            continue

        t_raw = evaluate_graph_ablation(
            graph,
            source_neuron_ids=source_neuron_ids,
            target_neuron_ids=target_neuron_ids,
            params=cfg,
            ablation_id=f"targeted_cell_loss_k{k}",
            removed_neuron_ids=targeted_hub_ids[:k],
        )
        curve_points.append(_enrich_curve_point("targeted_cell_loss", k, t_raw, base_m))

        c_raw = evaluate_graph_ablation(
            graph,
            source_neuron_ids=source_neuron_ids,
            target_neuron_ids=target_neuron_ids,
            params=cfg,
            ablation_id=f"matched_random_cell_loss_k{k}",
            removed_neuron_ids=matched_control_ids[:k],
        )
        curve_points.append(_enrich_curve_point("matched_random_cell_loss", k, c_raw, base_m))

    syn_arms: dict[str, dict[str, Any]] = {}
    syn_50_raw = evaluate_graph_ablation(
        graph,
        source_neuron_ids=source_neuron_ids,
        target_neuron_ids=target_neuron_ids,
        params=cfg,
        ablation_id="targeted_synapse_loss_50pct",
        edge_mask_pre_ids=targeted_hub_ids,
        edge_mask_post_ids=target_neuron_ids,
        edge_mask_factor=0.5,
    )
    syn_arms["targeted_synapse_loss_50pct"] = _enrich_curve_point(
        "targeted_synapse_loss", len(targeted_hub_ids), syn_50_raw, base_m
    )

    syn_100_raw = evaluate_graph_ablation(
        graph,
        source_neuron_ids=source_neuron_ids,
        target_neuron_ids=target_neuron_ids,
        params=cfg,
        ablation_id="targeted_synapse_loss_100pct",
        edge_mask_pre_ids=targeted_hub_ids,
        edge_mask_post_ids=target_neuron_ids,
        edge_mask_factor=0.0,
    )
    syn_arms["targeted_synapse_loss_100pct"] = _enrich_curve_point(
        "targeted_synapse_loss", len(targeted_hub_ids), syn_100_raw, base_m
    )

    if ctrl_syn_pre_ids and ctrl_syn_post_ids:
        syn_ctrl_raw = evaluate_graph_ablation(
            graph,
            source_neuron_ids=source_neuron_ids,
            target_neuron_ids=target_neuron_ids,
            params=cfg,
            ablation_id="matched_random_synapse_loss",
            edge_mask_pre_ids=ctrl_syn_pre_ids,
            edge_mask_post_ids=ctrl_syn_post_ids,
            edge_mask_factor=0.0,
        )
        syn_arms["matched_random_synapse_loss"] = _enrich_curve_point(
            "matched_random_synapse_loss", len(targeted_hub_ids), syn_ctrl_raw, base_m
        )

    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_level": cfg.model_level,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "dataset_id": graph.dataset_id,
        "release": graph.release,
        "specimen_id": graph.specimen_id,
        "source_graph_sha256": graph.graph_sha256(),
        "baseline": _enrich_curve_point("intact_baseline", 0, baseline_raw, base_m),
        "curve_points": curve_points,
        "synapse_ablation_arms": syn_arms,
    }


def _make_synthetic_graph(
    neuron_ids: Sequence[str],
    edges: Sequence[tuple[str, str, int]],
    *,
    tag: str,
) -> DirectedConnectomeGraph:
    return DirectedConnectomeGraph.from_edges(
        dataset_id=f"synthetic_{tag}",
        release="1.0",
        specimen_id="synthetic_specimen_01",
        is_synthetic_fixture=True,
        neuron_ids=neuron_ids,
        edges=[
            DirectedEdge(pre_source_id=u, post_source_id=v, synapse_count=c) for u, v, c in edges
        ],
        neurotransmitters=dict.fromkeys(neuron_ids, "EXCITATORY_SIGN"),
        aggregation_policy="error",
    )


def verify_topology_ablation_gates(
    params: TopologyAnalysisParameters | None = None,
) -> dict[str, Any]:
    """Verify all 5 analytic L0 topology, fragmentation, and ablation gates."""
    cfg = params or TopologyAnalysisParameters()

    # Gate 1: 5-node chain cut disconnects endpoints and yields 2 active WCCs of size 2
    g1 = _make_synthetic_graph(
        ["n0", "n1", "n2", "n3", "n4"],
        [("n0", "n1", 10), ("n1", "n2", 10), ("n2", "n3", 10), ("n3", "n4", 10)],
        tag="gate1_chain",
    )
    g1_base = evaluate_graph_ablation(
        g1, source_neuron_ids=["n0"], target_neuron_ids=["n4"], params=cfg, ablation_id="chain_base"
    )
    g1_cut = evaluate_graph_ablation(
        g1,
        source_neuron_ids=["n0"],
        target_neuron_ids=["n4"],
        params=cfg,
        ablation_id="chain_cut_n2",
        removed_neuron_ids=["n2"],
    )
    m1_c = g1_cut["metrics"]
    a1_c = g1_cut["audit"]
    gate1_ok = (
        g1_base["metrics"]["reachability_fraction"] == 1.0
        and m1_c["reachability_fraction"] == 0.0
        and m1_c["wcc_count"] == 2
        and m1_c["largest_wcc_nodes"] == 2
        and abs(m1_c["largest_wcc_fraction"] - 0.4) < 1e-12
        and a1_c["removed_node_count"] == 1
        and a1_c["removed_edge_count"] == 2
        and a1_c["removed_synapse_count"] == 20.0
    )

    # Gate 2: Diamond bridge dissociation: edge mask A->T retains A->B->T; node ablation A kills all
    g2 = _make_synthetic_graph(
        ["S", "A", "B", "T"],
        [
            ("S", "A", 20),
            ("A", "T", 25),
            ("S", "B", 5),
            ("A", "B", 20),
            ("B", "T", 20),
        ],
        tag="gate2_diamond",
    )
    g2_edge = evaluate_graph_ablation(
        g2,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        params=cfg,
        ablation_id="edge_cut_A_T",
        edge_mask_pre_ids=["A"],
        edge_mask_post_ids=["T"],
        edge_mask_factor=0.0,
    )
    g2_node = evaluate_graph_ablation(
        g2,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        params=cfg,
        ablation_id="node_cut_A",
        removed_neuron_ids=["A"],
    )
    gate2_ok = (
        g2_edge["audit"]["removed_edge_count"] == 1
        and g2_node["audit"]["removed_edge_count"] == 3
        and g2_edge["metrics"]["weighted_pathway_efficiency"]
        > g2_node["metrics"]["weighted_pathway_efficiency"]
        and g2_edge["metrics"]["three_hop_exc_flow"] > g2_node["metrics"]["three_hop_exc_flow"]
        and g2_node["metrics"]["three_hop_exc_flow"] == 0.0
    )

    # Gate 3: Asymmetric orientation & forward/reverse Dijkstra parity
    g3 = _make_synthetic_graph(
        ["S1", "S2", "S3", "H1", "T1"],
        [("S1", "H1", 8), ("S2", "H1", 12), ("S3", "H1", 15), ("H1", "T1", 20)],
        tag="gate3_asym",
    )
    # Reverse-triggered query: |src|=3 > |tgt|=1
    g3_rev = evaluate_graph_ablation(
        g3, source_neuron_ids=["S1", "S2", "S3"], target_neuron_ids=["T1"], params=cfg
    )
    # Transpose/direction test: T1 -> S1, S2, S3 (unreachable!) and forward single source
    g3_back = evaluate_graph_ablation(
        g3, source_neuron_ids=["T1"], target_neuron_ids=["S1", "S2", "S3"], params=cfg
    )
    g3_fwd_s1 = evaluate_graph_ablation(
        g3, source_neuron_ids=["S1"], target_neuron_ids=["T1"], params=cfg
    )
    g3_fwd_s2 = evaluate_graph_ablation(
        g3, source_neuron_ids=["S2"], target_neuron_ids=["T1"], params=cfg
    )
    g3_fwd_s3 = evaluate_graph_ablation(
        g3, source_neuron_ids=["S3"], target_neuron_ids=["T1"], params=cfg
    )
    expected_w_eff = (
        g3_fwd_s1["metrics"]["weighted_pathway_efficiency"]
        + g3_fwd_s2["metrics"]["weighted_pathway_efficiency"]
        + g3_fwd_s3["metrics"]["weighted_pathway_efficiency"]
    ) / 3.0
    gate3_ok = (
        g3_rev["metrics"]["reachability_fraction"] == 1.0
        and g3_back["metrics"]["reachability_fraction"] == 0.0
        and g3_back["metrics"]["weighted_pathway_efficiency"] == 0.0
        and abs(g3_rev["metrics"]["weighted_pathway_efficiency"] - expected_w_eff) < 1e-12
    )

    # Gate 4: Fractional synapse scaling monotonicity (1.0 -> 0.5 -> 0.0)
    g4 = _make_synthetic_graph(
        ["S", "H", "T"],
        [("S", "H", 10), ("H", "T", 20)],
        tag="gate4_frac",
    )
    r4_full = evaluate_graph_ablation(
        g4, source_neuron_ids=["S"], target_neuron_ids=["T"], params=cfg
    )
    r4_half = evaluate_graph_ablation(
        g4,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        params=cfg,
        ablation_id="half_syn",
        edge_mask_pre_ids=["H"],
        edge_mask_post_ids=["T"],
        edge_mask_factor=0.5,
    )
    r4_zero = evaluate_graph_ablation(
        g4,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        params=cfg,
        ablation_id="zero_syn",
        edge_mask_pre_ids=["H"],
        edge_mask_post_ids=["T"],
        edge_mask_factor=0.0,
    )
    gate4_ok = (
        r4_half["audit"]["removed_synapse_count"] == 10.0
        and r4_full["metrics"]["two_hop_exc_flow"] == 200.0
        and r4_half["metrics"]["two_hop_exc_flow"] == 100.0
        and r4_zero["metrics"]["two_hop_exc_flow"] == 0.0
        and (
            r4_full["metrics"]["weighted_pathway_efficiency"]
            > r4_half["metrics"]["weighted_pathway_efficiency"]
            > r4_zero["metrics"]["weighted_pathway_efficiency"]
        )
    )

    # Gate 5: Isolated off-pathway control invariance & immutability
    g5 = _make_synthetic_graph(
        ["S", "H", "T", "C1", "C2"],
        [("S", "H", 10), ("H", "T", 20), ("C1", "C2", 50)],
        tag="gate5_ctrl",
    )
    sha_before = g5.graph_sha256()
    r5_base = evaluate_graph_ablation(
        g5, source_neuron_ids=["S"], target_neuron_ids=["T"], params=cfg
    )
    r5_ctrl = evaluate_graph_ablation(
        g5,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        params=cfg,
        ablation_id="ctrl_cut",
        removed_neuron_ids=["C1"],
    )
    sha_after = g5.graph_sha256()
    gate5_ok = (
        sha_before == sha_after
        and r5_ctrl["metrics"]["weighted_pathway_efficiency"]
        == r5_base["metrics"]["weighted_pathway_efficiency"]
        and r5_ctrl["metrics"]["two_hop_exc_flow"] == r5_base["metrics"]["two_hop_exc_flow"]
        and r5_ctrl["audit"]["removed_node_count"] == 1
        and r5_ctrl["audit"]["removed_synapse_count"] == 50.0
    )

    gates = {
        "chain_cut_disconnects": {
            "passed": bool(gate1_ok),
            "baseline_reachability": g1_base["metrics"]["reachability_fraction"],
            "cut_reachability": m1_c["reachability_fraction"],
            "cut_wcc_count": m1_c["wcc_count"],
            "cut_largest_wcc_fraction": m1_c["largest_wcc_fraction"],
            "removed_edge_count": a1_c["removed_edge_count"],
        },
        "parallel_bridge_node_vs_edge_dissociation": {
            "passed": bool(gate2_ok),
            "edge_cut_removed_edges": g2_edge["audit"]["removed_edge_count"],
            "node_cut_removed_edges": g2_node["audit"]["removed_edge_count"],
            "edge_cut_weighted_eff": round(g2_edge["metrics"]["weighted_pathway_efficiency"], 6),
            "node_cut_weighted_eff": round(g2_node["metrics"]["weighted_pathway_efficiency"], 6),
            "edge_cut_3hop_flow": g2_edge["metrics"]["three_hop_exc_flow"],
            "node_cut_3hop_flow": g2_node["metrics"]["three_hop_exc_flow"],
        },
        "asymmetric_orientation_and_reverse_dijkstra_parity": {
            "passed": bool(gate3_ok),
            "forward_reachability": g3_rev["metrics"]["reachability_fraction"],
            "transpose_reachability": g3_back["metrics"]["reachability_fraction"],
            "reverse_dijkstra_weighted_eff": round(
                g3_rev["metrics"]["weighted_pathway_efficiency"], 9
            ),
            "expected_forward_weighted_eff": round(expected_w_eff, 9),
        },
        "fractional_synapse_scaling_monotonicity": {
            "passed": bool(gate4_ok),
            "flow_full": r4_full["metrics"]["two_hop_exc_flow"],
            "flow_half": r4_half["metrics"]["two_hop_exc_flow"],
            "flow_zero": r4_zero["metrics"]["two_hop_exc_flow"],
            "lost_synapses_half": r4_half["audit"]["removed_synapse_count"],
        },
        "isolated_control_invariance_and_immutability": {
            "passed": bool(gate5_ok),
            "graph_sha_unchanged": sha_before == sha_after,
            "ctrl_weighted_eff": round(r5_ctrl["metrics"]["weighted_pathway_efficiency"], 9),
            "baseline_weighted_eff": round(r5_base["metrics"]["weighted_pathway_efficiency"], 9),
            "ctrl_2hop_flow": r5_ctrl["metrics"]["two_hop_exc_flow"],
        },
    }
    overall = all(bool(item["passed"]) for item in gates.values())
    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "overall_passed": overall,
        "gates": gates,
    }


__all__ = [
    "AblationAuditRecord",
    "TopologyAnalysisParameters",
    "TopologyIntegrityMetrics",
    "evaluate_graph_ablation",
    "run_progressive_ablation_curve",
    "verify_topology_ablation_gates",
]
