"""Bounded subgraph extraction with explicit boundary-omission accounting."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from synapse_core.types import DirectedConnectomeGraph


class SubgraphBoundExceededError(ValueError):
    """Raised when bounded BFS discovers more neurons than max_nodes allows."""


class SubgraphMetadata(BaseModel):
    """Complete provenance and truncation metadata required by AGENTS.md section 6.2."""

    model_config = ConfigDict(frozen=True)

    selection_rule: str
    seed_neuron_ids: tuple[str, ...]
    allowed_regions: tuple[str, ...] | None
    allowed_cell_types: tuple[str, ...] | None
    hop_limit: int
    min_synapse_threshold: int
    direction: Literal["outgoing", "incoming", "both"]
    boundary_policy: Literal["induced"]
    source_dataset_id: str
    source_release: str
    source_specimen_id: str
    source_graph_sha256: str
    subgraph_sha256: str
    n_seed_neurons: int
    n_selected_neurons: int
    n_selected_edges: int
    total_selected_synapses: int
    omitted_incoming_edge_count: int
    omitted_incoming_synapse_count: int
    omitted_outgoing_edge_count: int
    omitted_outgoing_synapse_count: int
    isolation_limitations: tuple[str, ...]


def extract_bounded_subgraph(
    graph: DirectedConnectomeGraph,
    *,
    seed_neuron_ids: Sequence[str],
    hop_limit: int,
    direction: Literal["outgoing", "incoming", "both"] = "outgoing",
    min_synapse_threshold: int = 1,
    max_nodes: int | None = None,
    allowed_neuron_ids: Sequence[str] | None = None,
    selection_rule: str | None = None,
    allowed_regions: Sequence[str] | None = None,
    allowed_cell_types: Sequence[str] | None = None,
) -> tuple[DirectedConnectomeGraph, SubgraphMetadata]:
    """Extract an induced subgraph by bounded BFS and compute exact omitted boundary traffic.

    Traversal follows edges with ``synapse_count >= min_synapse_threshold`` up to
    ``hop_limit`` steps from ``seed_neuron_ids``. The returned subgraph preserves all directed
    edges present in ``graph`` among the selected neuron set (``boundary_policy='induced'``).
    """
    if not seed_neuron_ids:
        raise ValueError("seed_neuron_ids must not be empty")
    if isinstance(hop_limit, bool) or hop_limit < 0:
        raise ValueError(f"hop_limit must be an integer >= 0, got {hop_limit}")
    if isinstance(min_synapse_threshold, bool) or min_synapse_threshold < 1:
        raise ValueError(
            f"min_synapse_threshold must be an integer >= 1, got {min_synapse_threshold}"
        )
    if direction not in ("outgoing", "incoming", "both"):
        raise ValueError(f"Invalid direction {direction!r}")

    unique_seeds = tuple(dict.fromkeys(seed_neuron_ids))
    seed_indices = [graph.index_of(nid) for nid in unique_seeds]
    if max_nodes is not None and max_nodes < len(seed_indices):
        raise SubgraphBoundExceededError(
            f"Seed count {len(seed_indices)} already exceeds max_nodes={max_nodes}"
        )

    n = graph.n_neurons
    allowed_mask = np.ones(n, dtype=bool)
    if allowed_neuron_ids is not None:
        allowed_mask[:] = False
        for nid in allowed_neuron_ids:
            allowed_mask[graph.index_of(nid)] = True
        for idx, nid in zip(seed_indices, unique_seeds, strict=True):
            if not allowed_mask[idx]:
                raise ValueError(f"Seed neuron {nid!r} is excluded by allowed_neuron_ids")

    w_csr = graph.adjacency_copy()  # row = post_idx, col = pre_idx
    w_csc = w_csr.tocsc()  # fast outgoing lookup by column = pre_idx

    visited: set[int] = set(seed_indices)
    queue: deque[tuple[int, int]] = deque((idx, 0) for idx in seed_indices)

    while queue:
        node_idx, depth = queue.popleft()
        if depth >= hop_limit:
            continue

        neighbors: list[int] = []
        if direction in ("outgoing", "both"):
            c_start = int(w_csc.indptr[node_idx])
            c_end = int(w_csc.indptr[node_idx + 1])
            out_rows = w_csc.indices[c_start:c_end]
            out_cnts = w_csc.data[c_start:c_end]
            neighbors.extend(out_rows[out_cnts >= min_synapse_threshold].tolist())

        if direction in ("incoming", "both"):
            r_start = int(w_csr.indptr[node_idx])
            r_end = int(w_csr.indptr[node_idx + 1])
            in_cols = w_csr.indices[r_start:r_end]
            in_cnts = w_csr.data[r_start:r_end]
            neighbors.extend(in_cols[in_cnts >= min_synapse_threshold].tolist())

        for nbr in neighbors:
            if not allowed_mask[nbr] or nbr in visited:
                continue
            visited.add(nbr)
            if max_nodes is not None and len(visited) > max_nodes:
                raise SubgraphBoundExceededError(
                    f"Bounded BFS exceeded max_nodes={max_nodes} at depth {depth + 1}"
                )
            queue.append((nbr, depth + 1))

    selected_idx = np.array(sorted(visited), dtype=np.int64)
    in_set = np.zeros(n, dtype=bool)
    in_set[selected_idx] = True

    sub_adj = w_csr[selected_idx, :][:, selected_idx].tocsr()
    sub_neuron_ids = tuple(graph.neuron_ids[int(i)] for i in selected_idx)
    sub_nts = tuple(graph.neurotransmitters[int(i)] for i in selected_idx)

    subgraph = DirectedConnectomeGraph(
        dataset_id=graph.dataset_id,
        release=graph.release,
        specimen_id=graph.specimen_id,
        is_synthetic_fixture=graph.is_synthetic_fixture,
        neuron_ids=sub_neuron_ids,
        neurotransmitters=sub_nts,
        adjacency_counts=sub_adj,
        aggregation_policy=graph.aggregation_policy,
    )

    # Boundary omissions: incoming edges (pre not in S -> post in S)
    rows_in_s = w_csr[selected_idx, :]
    omitted_in_mask = ~in_set[rows_in_s.indices]
    omitted_in_edges = int(np.count_nonzero(omitted_in_mask))
    omitted_in_synapses = int(rows_in_s.data[omitted_in_mask].sum())

    # Boundary omissions: outgoing edges (pre in S -> post not in S)
    cols_in_s = w_csc[:, selected_idx]
    omitted_out_mask = ~in_set[cols_in_s.indices]
    omitted_out_edges = int(np.count_nonzero(omitted_out_mask))
    omitted_out_synapses = int(cols_in_s.data[omitted_out_mask].sum())

    default_rule = (
        f"bfs(direction={direction}, hop_limit={hop_limit}, "
        f"min_synapse_threshold={min_synapse_threshold}, boundary_policy=induced)"
    )
    meta = SubgraphMetadata(
        selection_rule=default_rule if selection_rule is None else selection_rule,
        seed_neuron_ids=unique_seeds,
        allowed_regions=None if allowed_regions is None else tuple(allowed_regions),
        allowed_cell_types=None if allowed_cell_types is None else tuple(allowed_cell_types),
        hop_limit=hop_limit,
        min_synapse_threshold=min_synapse_threshold,
        direction=direction,
        boundary_policy="induced",
        source_dataset_id=graph.dataset_id,
        source_release=graph.release,
        source_specimen_id=graph.specimen_id,
        source_graph_sha256=graph.graph_sha256(),
        subgraph_sha256=subgraph.graph_sha256(),
        n_seed_neurons=len(unique_seeds),
        n_selected_neurons=subgraph.n_neurons,
        n_selected_edges=subgraph.n_edges,
        total_selected_synapses=subgraph.total_synapses,
        omitted_incoming_edge_count=omitted_in_edges,
        omitted_incoming_synapse_count=omitted_in_synapses,
        omitted_outgoing_edge_count=omitted_out_edges,
        omitted_outgoing_synapse_count=omitted_out_synapses,
        isolation_limitations=(
            "Induced subgraphs are not dynamically equivalent to the full connectome.",
            f"Omitted {omitted_in_edges} incoming boundary edges "
            f"({omitted_in_synapses} synapses) from unselected neurons.",
            f"Omitted {omitted_out_edges} outgoing boundary edges "
            f"({omitted_out_synapses} synapses) to unselected neurons.",
        ),
    )
    return subgraph, meta
