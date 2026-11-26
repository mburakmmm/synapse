"""Unit tests for L0 connectome topology, fragmentation, and exact ablation audits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from synapse_cli.main import main as cli_main
from synapse_core import (
    DirectedConnectomeGraph,
    DirectedEdge,
    TopologyAnalysisParameters,
    evaluate_graph_ablation,
    run_progressive_ablation_curve,
    verify_topology_ablation_gates,
)


@pytest.mark.unit
def test_topology_parameter_validation_and_canonical_hash() -> None:
    p1 = TopologyAnalysisParameters()
    p2 = TopologyAnalysisParameters()
    assert p1.canonical_sha256() == p2.canonical_sha256()
    assert p1.model_level == "L0"
    assert p1.model_id == "neuro_topology_ablation_v1"

    with pytest.raises(ValidationError):
        TopologyAnalysisParameters(min_synapse_threshold=0)
    with pytest.raises(ValidationError):
        TopologyAnalysisParameters(min_synapse_threshold=False)


@pytest.mark.unit
def test_topology_gates_and_asymmetric_dijkstra_parity() -> None:
    params = TopologyAnalysisParameters()
    report = verify_topology_ablation_gates(params)
    assert report["overall_passed"] is True
    for g in report["gates"].values():
        assert g["passed"] is True

    # Build asymmetric multi-source/multi-target graph covering both len(src)>len(tgt) and <
    nids = ["S1", "S2", "S3", "H1", "H2", "T1", "T2"]
    edges = [
        DirectedEdge(pre_source_id="S1", post_source_id="H1", synapse_count=12),
        DirectedEdge(pre_source_id="S2", post_source_id="H1", synapse_count=8),
        DirectedEdge(pre_source_id="S3", post_source_id="H2", synapse_count=20),
        DirectedEdge(pre_source_id="H1", post_source_id="T1", synapse_count=15),
        DirectedEdge(pre_source_id="H1", post_source_id="T2", synapse_count=10),
        DirectedEdge(pre_source_id="H2", post_source_id="T1", synapse_count=25),
    ]
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="synthetic_asym_unit",
        release="1.0",
        specimen_id="synthetic_01",
        is_synthetic_fixture=True,
        neuron_ids=nids,
        edges=edges,
        neurotransmitters=dict.fromkeys(nids, "ACH"),
    )
    res_many_to_one = evaluate_graph_ablation(
        g, source_neuron_ids=["S1", "S2", "S3"], target_neuron_ids=["T1"], params=params
    )
    pair_effs = [
        evaluate_graph_ablation(
            g, source_neuron_ids=[src], target_neuron_ids=["T1"], params=params
        )["metrics"]["weighted_pathway_efficiency"]
        for src in ("S1", "S2", "S3")
    ]
    assert res_many_to_one["metrics"]["weighted_pathway_efficiency"] == pytest.approx(
        sum(pair_effs) / 3.0, abs=1e-12
    )
    # Transpose direction T1 -> S1,S2,S3 must have zero reachability
    res_reverse = evaluate_graph_ablation(
        g, source_neuron_ids=["T1"], target_neuron_ids=["S1", "S2", "S3"], params=params
    )
    assert res_reverse["metrics"]["reachability_fraction"] == 0.0

    with pytest.raises(ValueError, match="edge_mask_factor"):
        evaluate_graph_ablation(
            g,
            source_neuron_ids=["S1"],
            target_neuron_ids=["T1"],
            edge_mask_pre_ids=["H1"],
            edge_mask_post_ids=["T1"],
            edge_mask_factor=1.5,
        )


@pytest.mark.unit
def test_progressive_attack_curve_and_cli_verify(tmp_path: Path) -> None:
    nids = ["S", "H1", "H2", "C1", "C2", "C_POST", "T"]
    edges = [
        DirectedEdge(pre_source_id="S", post_source_id="H1", synapse_count=20),
        DirectedEdge(pre_source_id="H1", post_source_id="T", synapse_count=30),
        DirectedEdge(pre_source_id="S", post_source_id="H2", synapse_count=10),
        DirectedEdge(pre_source_id="H2", post_source_id="T", synapse_count=10),
        DirectedEdge(pre_source_id="C1", post_source_id="C_POST", synapse_count=20),
        DirectedEdge(pre_source_id="C2", post_source_id="C_POST", synapse_count=20),
    ]
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="synthetic_curve_unit",
        release="1.0",
        specimen_id="synthetic_02",
        is_synthetic_fixture=True,
        neuron_ids=nids,
        edges=edges,
        neurotransmitters=dict.fromkeys(nids, "EXCITATORY_SIGN"),
    )
    sha_before = g.graph_sha256()
    curve = run_progressive_ablation_curve(
        g,
        source_neuron_ids=["S"],
        target_neuron_ids=["T"],
        targeted_hub_ids=["H1", "H2"],
        matched_control_ids=["C1", "C2"],
        ctrl_syn_pre_ids=["C1", "C2"],
        ctrl_syn_post_ids=["C_POST"],
        step_counts=(0, 1, 2),
    )
    assert g.graph_sha256() == sha_before
    tgt_k2 = next(
        p
        for p in curve["curve_points"]
        if p["arm_type"] == "targeted_cell_loss" and p["step_k"] == 2
    )
    ctrl_k2 = next(
        p
        for p in curve["curve_points"]
        if p["arm_type"] == "matched_random_cell_loss" and p["step_k"] == 2
    )
    assert tgt_k2["weighted_eff_ratio"] == 0.0
    assert tgt_k2["audit"]["removed_edges_sha256"]
    assert ctrl_k2["weighted_eff_ratio"] == 1.0
    assert (
        curve["synapse_ablation_arms"]["matched_random_synapse_loss"]["weighted_eff_ratio"] == 1.0
    )

    out_dir = tmp_path / "topo_verify"
    rc = cli_main(["topology", "verify", "--out-dir", str(out_dir), "--json"])
    assert rc == 0
    saved = json.loads((out_dir / "l0_verification_gate.json").read_text(encoding="utf-8"))
    assert saved["overall_passed"] is True
