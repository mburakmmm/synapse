"""Unit tests for bounded subgraph extraction, boundary omissions, and immutability."""

from __future__ import annotations

import numpy as np
import pytest

from synapse_core import (
    DirectedConnectomeGraph,
    SubgraphBoundExceededError,
    extract_bounded_subgraph,
)


def _toy_directed_graph() -> DirectedConnectomeGraph:
    # A -> B (10), B -> C (8), C -> D (12), X -> B (5), C -> Y (4), A -> Z (1 weak)
    return DirectedConnectomeGraph.from_arrays(
        dataset_id="toy",
        release="1.0",
        specimen_id="toy0",
        is_synthetic_fixture=True,
        neuron_ids=("A", "B", "C", "D", "X", "Y", "Z"),
        pre_indices=np.array([0, 1, 2, 4, 2, 0]),
        post_indices=np.array([1, 2, 3, 1, 5, 6]),
        counts=np.array([10, 8, 12, 5, 4, 1]),
        neurotransmitters=("ACH", "ACH", "GABA", "ACH", "ACH", "ACH", "ACH"),
    )


@pytest.mark.unit
def test_bounded_outgoing_subgraph_and_boundary_omissions() -> None:
    g = _toy_directed_graph()
    sub, meta = extract_bounded_subgraph(
        g,
        seed_neuron_ids=("A",),
        hop_limit=2,
        direction="outgoing",
        min_synapse_threshold=2,
    )
    # 1-hop from A (>=2 syn): B (excludes Z since weight 1 < 2)
    # 2-hop from B (>=2 syn): C
    assert set(sub.neuron_ids) == {"A", "B", "C"}
    assert sub.n_edges == 2
    assert sub.edge_count_between("A", "B") == 10
    assert sub.edge_count_between("B", "C") == 8
    # Incoming boundary omission: X -> B (5 synapses)
    assert meta.omitted_incoming_edge_count == 1
    assert meta.omitted_incoming_synapse_count == 5
    # Outgoing boundary omissions: C -> D (12), C -> Y (4), A -> Z (1) = 3 edges, 17 synapses
    assert meta.omitted_outgoing_edge_count == 3
    assert meta.omitted_outgoing_synapse_count == 17
    assert meta.source_graph_sha256 == g.graph_sha256()
    assert meta.subgraph_sha256 == sub.graph_sha256()
    assert "not dynamically equivalent" in meta.isolation_limitations[0]


@pytest.mark.unit
def test_bounded_incoming_direction_and_max_nodes_guard() -> None:
    g = _toy_directed_graph()
    sub_in, _ = extract_bounded_subgraph(
        g,
        seed_neuron_ids=("B",),
        hop_limit=1,
        direction="incoming",
        min_synapse_threshold=5,
    )
    assert set(sub_in.neuron_ids) == {"A", "X", "B"}
    assert sub_in.edge_count_between("A", "B") == 10
    assert sub_in.edge_count_between("X", "B") == 5

    with pytest.raises(SubgraphBoundExceededError, match="max_nodes=2"):
        extract_bounded_subgraph(
            g,
            seed_neuron_ids=("B",),
            hop_limit=1,
            direction="incoming",
            max_nodes=2,
        )


@pytest.mark.unit
def test_from_arrays_permutation_invariant_hash_and_duplicate_check() -> None:
    g1 = _toy_directed_graph()
    # Permute neuron order reversed
    rev_ids = tuple(reversed(g1.neuron_ids))
    rev_nts = tuple(reversed(g1.neurotransmitters))
    pre, post, cnt = g1.edge_arrays()
    n = g1.n_neurons
    g2 = DirectedConnectomeGraph.from_arrays(
        dataset_id="toy",
        release="1.0",
        specimen_id="toy0",
        is_synthetic_fixture=True,
        neuron_ids=rev_ids,
        pre_indices=(n - 1) - pre,
        post_indices=(n - 1) - post,
        counts=cnt,
        neurotransmitters=rev_nts,
    )
    assert g1.graph_sha256() == g2.graph_sha256()

    with pytest.raises(ValueError, match="Duplicate directed edge"):
        DirectedConnectomeGraph.from_arrays(
            dataset_id="toy",
            release="1.0",
            specimen_id="toy0",
            is_synthetic_fixture=True,
            neuron_ids=("A", "B"),
            pre_indices=np.array([0, 0]),
            post_indices=np.array([1, 1]),
            counts=np.array([2, 3]),
            aggregation_policy="error",
        )
