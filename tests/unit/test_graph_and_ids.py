"""Unit tests for 64-bit ID preservation, sparse graph orientation, and NT policies."""

from __future__ import annotations

import numpy as np
import pytest

from synapse_core import DirectedConnectomeGraph, DirectedEdge, NeuronNamespaceKey


@pytest.mark.unit
def test_64bit_neuron_id_round_trip() -> None:
    # Exceeds IEEE-754 float64 exact integer boundary (2**53 = 9007199254740992)
    large_id = "720575940621039143"
    key = NeuronNamespaceKey(
        dataset_id="flywire_fafb",
        release="v630",
        specimen_id="FAFB_female_01",
        source_neuron_id=large_id,
    )
    serialized = key.to_key()
    restored = NeuronNamespaceKey.from_key(serialized)
    assert restored == key
    assert restored.source_neuron_id == large_id


@pytest.mark.unit
def test_asymmetric_sparse_orientation_detects_transpose() -> None:
    # Edge: n0 -> n1 (weight 15). No edge n1 -> n0.
    graph = DirectedConnectomeGraph.from_edges(
        dataset_id="synth",
        release="1.0",
        specimen_id="spec0",
        is_synthetic_fixture=True,
        neuron_ids=("9007199254740993", "9007199254740994"),
        edges=[
            DirectedEdge("9007199254740993", "9007199254740994", 15),
        ],
        neurotransmitters={"9007199254740993": "ACH", "9007199254740994": "GABA"},
    )
    adj = graph.adjacency_copy()
    # Explicit contract: row = post_idx, col = pre_idx, so W[1, 0] == 15 and W[0, 1] == 0
    assert adj[1, 0] == 15
    assert adj[0, 1] == 0

    pre_active = np.array([1.0, 0.0])
    post_input = adj @ pre_active
    np.testing.assert_allclose(post_input, np.array([0.0, 15.0]))
    assert not np.allclose(adj.T @ pre_active, post_input)


@pytest.mark.unit
def test_self_loops_reciprocal_and_duplicate_policy() -> None:
    edges = [
        DirectedEdge("A", "A", 3),  # self-loop
        DirectedEdge("A", "B", 10),
        DirectedEdge("B", "A", 4),  # reciprocal
    ]
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="synth",
        release="1.0",
        specimen_id="spec0",
        is_synthetic_fixture=True,
        neuron_ids=("A", "B"),
        edges=edges,
        aggregation_policy="error",
    )
    assert g.edge_count_between("A", "A") == 3
    assert g.edge_count_between("A", "B") == 10
    assert g.edge_count_between("B", "A") == 4
    assert g.total_synapses == 17

    # Duplicate (A -> B) must fail under aggregation_policy='error'
    with pytest.raises(ValueError, match="Duplicate directed edge"):
        DirectedConnectomeGraph.from_edges(
            dataset_id="synth",
            release="1.0",
            specimen_id="spec0",
            is_synthetic_fixture=True,
            neuron_ids=("A", "B"),
            edges=[DirectedEdge("A", "B", 5), DirectedEdge("A", "B", 7)],
            aggregation_policy="error",
        )

    # Under aggregation_policy='sum', duplicates aggregate cleanly
    g_sum = DirectedConnectomeGraph.from_edges(
        dataset_id="synth",
        release="1.0",
        specimen_id="spec0",
        is_synthetic_fixture=True,
        neuron_ids=("A", "B"),
        edges=[DirectedEdge("A", "B", 5), DirectedEdge("A", "B", 7)],
        aggregation_policy="sum",
    )
    assert g_sum.edge_count_between("A", "B") == 12


@pytest.mark.unit
def test_unknown_neurotransmitter_never_defaults_excitatory() -> None:
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="synth",
        release="1.0",
        specimen_id="spec0",
        is_synthetic_fixture=True,
        neuron_ids=("PRE_UNK", "PRE_GABA", "POST"),
        edges=[
            DirectedEdge("PRE_UNK", "POST", 10),
            DirectedEdge("PRE_GABA", "POST", 5),
        ],
        neurotransmitters={"PRE_UNK": None, "PRE_GABA": "GABA", "POST": "ACH"},
    )
    w_zero = g.signed_weight_matrix(0.000275, unknown_nt_policy="zero_effect")
    assert w_zero[2, 0] == 0.0
    assert w_zero[2, 1] == pytest.approx(-5 * 0.000275)

    with pytest.raises(ValueError, match="Unknown neurotransmitter"):
        g.signed_weight_matrix(0.000275, unknown_nt_policy="error")


@pytest.mark.unit
def test_adjacency_copy_does_not_mutate_graph() -> None:
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="synth",
        release="1.0",
        specimen_id="spec0",
        is_synthetic_fixture=True,
        neuron_ids=("A", "B"),
        edges=[DirectedEdge("A", "B", 8)],
    )
    mat = g.adjacency_copy()
    mat[1, 0] = 999
    assert g.edge_count_between("A", "B") == 8
