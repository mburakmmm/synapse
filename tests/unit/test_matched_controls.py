"""Unit tests for structurally matched control neuron selection."""

from __future__ import annotations

import pytest

from synapse_core import DirectedConnectomeGraph, DirectedEdge
from synapse_experiments import select_matched_control_neurons


def _build_stratified_graph() -> DirectedConnectomeGraph:
    # Build 2 excitatory targets (T1, T2), 2 downstream cells (D1, D2) with high degree,
    # 4 valid non-downstream excitatory controls (C1..C4), and 2 inhibitory decoys (I1..I2).
    neuron_ids = ("T1", "T2", "D1", "D2", "C1", "C2", "C3", "C4", "I1", "I2", "SINK1", "SINK2")
    nts = {
        "T1": "EXCITATORY_SIGN",
        "T2": "EXCITATORY_SIGN",
        "D1": "EXCITATORY_SIGN",
        "D2": "EXCITATORY_SIGN",
        "C1": "EXCITATORY_SIGN",
        "C2": "EXCITATORY_SIGN",
        "C3": "EXCITATORY_SIGN",
        "C4": "EXCITATORY_SIGN",
        "I1": "INHIBITORY_SIGN",
        "I2": "INHIBITORY_SIGN",
        "SINK1": "EXCITATORY_SIGN",
        "SINK2": "EXCITATORY_SIGN",
    }
    edges = [
        # Targets project to D1, D2, and SINK1
        DirectedEdge("T1", "D1", 10),
        DirectedEdge("T1", "SINK1", 8),
        DirectedEdge("T2", "D2", 6),
        # D1 and D2 match T1/T2 degrees but are 1-hop downstream (must be excluded)
        DirectedEdge("D1", "SINK1", 10),
        DirectedEdge("D1", "SINK2", 8),
        DirectedEdge("D2", "SINK2", 6),
        # Valid non-downstream controls matching T1 (out_deg=2, syn=18) and T2 (out_deg=1, syn=6)
        DirectedEdge("C1", "SINK1", 10),
        DirectedEdge("C1", "SINK2", 8),
        DirectedEdge("C2", "SINK2", 6),
        # Mismatched weak excitatory decoys
        DirectedEdge("C3", "SINK1", 1),
        DirectedEdge("C4", "SINK2", 1),
        # Inhibitory decoys with identical degrees to T1/T2 (must never match excitatory targets)
        DirectedEdge("I1", "SINK1", 10),
        DirectedEdge("I1", "SINK2", 8),
        DirectedEdge("I2", "SINK2", 6),
    ]
    return DirectedConnectomeGraph.from_edges(
        dataset_id="synth_ctrl",
        release="1.0",
        specimen_id="s0",
        is_synthetic_fixture=True,
        neuron_ids=neuron_ids,
        edges=edges,
        neurotransmitters=nts,
    )


@pytest.mark.unit
def test_select_matched_controls_excludes_downstream_matches_nt_and_is_deterministic() -> None:
    graph = _build_stratified_graph()
    res1 = select_matched_control_neurons(
        graph,
        target_neuron_ids=("T1", "T2"),
        seed=123,
        exclude_neuron_ids=("SINK1",),
        exclude_1hop_downstream_of_targets=True,
    )
    res2 = select_matched_control_neurons(
        graph,
        target_neuron_ids=("T1", "T2"),
        seed=123,
        exclude_neuron_ids=("SINK1",),
        exclude_1hop_downstream_of_targets=True,
    )
    assert res1 == res2
    ctrls = res1["control_neuron_ids"]
    assert len(ctrls) == 2
    assert len(set(ctrls)) == 2
    # Must choose C1 and C2 (never D1/D2 downstream or I1/I2 wrong NT or SINK1 excluded)
    assert set(ctrls) == {"C1", "C2"}
    assert abs(res1["residual_imbalance"]["out_degree"]["smd"]) < 1e-6
    assert abs(res1["residual_imbalance"]["out_synapses"]["smd"]) < 1e-6

    # Disabling 1-hop exclusion fails when insufficient candidates exist beyond limits
    with pytest.raises(ValueError, match="Insufficient eligible"):
        select_matched_control_neurons(
            graph,
            target_neuron_ids=("T1", "T2"),
            exclude_neuron_ids=("D1", "D2", "C1", "C2", "C3", "C4", "SINK1", "SINK2"),
        )
