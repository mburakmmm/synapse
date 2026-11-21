"""Unit tests for pathway-specific EdgeMaskModulation and windowed persistence summaries."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from synapse_analysis import compute_windowed_response_metrics
from synapse_core import (
    Brian2CPUBackend,
    ConstantCurrentStimulus,
    DirectedConnectomeGraph,
    DirectedEdge,
    EdgeMaskModulation,
    LIFParameters,
    NeuronSilencing,
    SeedRecord,
    SimulationRequest,
)
from synapse_experiments import ProtocolValidationError, load_and_validate_protocol


@pytest.mark.unit
def test_edge_mask_disinhibits_only_selected_pathway_without_mutating_graph() -> None:
    """Masking GABA A -> B disinhibits B while leaving GABA A -> C intact."""
    graph = DirectedConnectomeGraph.from_edges(
        dataset_id="unit_edge_mask",
        release="v1",
        specimen_id="spec",
        is_synthetic_fixture=True,
        neuron_ids=("inhib_A", "target_B", "target_C"),
        edges=(
            DirectedEdge("inhib_A", "target_B", 20),
            DirectedEdge("inhib_A", "target_C", 20),
        ),
        neurotransmitters={"inhib_A": "GABA", "target_B": "ACH", "target_C": "ACH"},
    )
    snap_before = graph.graph_sha256()

    params = LIFParameters(solver="exact", dg_unless_refractory=False)
    seed_rec = SeedRecord(
        algorithm="sha256",
        master_seed=1,
        derived_seeds={"brian2": 42},
    )
    backend = Brian2CPUBackend()

    # Drive inhib_A and both excitatory outputs strongly with constant current
    stim_all = ConstantCurrentStimulus(
        target_neuron_ids=("inhib_A", "target_B", "target_C"),
        current_a=2.0e-9,
        start_s=0.0,
        end_s=0.3,
    )

    res_base = backend.run(
        SimulationRequest(
            graph=graph,
            parameters=params,
            duration_s=0.3,
            seed_record=seed_rec,
            interventions=(stim_all,),
        )
    )
    res_mask_b = backend.run(
        SimulationRequest(
            graph=graph,
            parameters=params,
            duration_s=0.3,
            seed_record=seed_rec,
            interventions=(
                stim_all,
                EdgeMaskModulation(
                    pre_neuron_ids=("inhib_A",),
                    post_neuron_ids=("target_B",),
                    factor=0.0,
                ),
            ),
        )
    )
    res_silence_a = backend.run(
        SimulationRequest(
            graph=graph,
            parameters=params,
            duration_s=0.3,
            seed_record=seed_rec,
            interventions=(
                stim_all,
                NeuronSilencing(target_neuron_ids=("inhib_A",), mode="both_zero"),
            ),
        )
    )

    assert graph.graph_sha256() == snap_before

    b_base, c_base = float(res_base.firing_rates_hz[1]), float(res_base.firing_rates_hz[2])
    b_mask, c_mask = float(res_mask_b.firing_rates_hz[1]), float(res_mask_b.firing_rates_hz[2])
    b_sil, c_sil = (
        float(res_silence_a.firing_rates_hz[1]),
        float(res_silence_a.firing_rates_hz[2]),
    )

    # Disinhibition raises B firing, leaves C identical to baseline under edge_mask,
    # while global cell silencing raises both B and C symmetrically.
    assert b_mask > b_base
    assert c_mask == pytest.approx(c_base)
    assert b_sil == pytest.approx(b_mask)
    assert c_sil == pytest.approx(b_mask)
    assert c_sil > c_base

    mask_rec = res_mask_b.resolved_interventions[1]
    assert mask_rec.kind == "edge_mask"
    assert mask_rec.affected_edge_count == 1
    assert mask_rec.resolved_target_ids == ("inhib_A", "target_B")


@pytest.mark.unit
def test_protocol_validates_edge_mask_endpoints(tmp_path: Path) -> None:
    proto_path = tmp_path / "edge_mask_proto.yaml"
    proto_doc = {
        "schema_version": "1.0",
        "protocol_id": "UNIT-EDGE-MASK",
        "revision": 1,
        "status": "draft",
        "analysis_intent": "exploratory",
        "question": "Does edge_mask validation fail closed on empty endpoints?",
        "hypothesis": "Engineering protocol test.",
        "biological_unit": "synthetic",
        "simulation_unit": "paired_seed_run",
        "sources": [{"dataset_id": "synth", "release": "v1", "manifest_sha256": "abc"}],
        "model": {
            "id": "synapse_lif_v1",
            "revision": "1.0",
            "parameter_manifest_sha256": LIFParameters().canonical_sha256(),
            "backend": "brian2_cpu",
        },
        "conditions": [
            {
                "id": "mask_cond",
                "interventions": [
                    {
                        "kind": "edge_mask",
                        "pre_neuron_ids": ["a"],
                        "post_neuron_ids": [],
                        "factor": 0.0,
                    }
                ],
            }
        ],
        "stimulus_schedule": {"duration_s": 0.2, "stimuli": []},
        "measurement_window": {"start_s": 0.0, "end_s": 0.2},
        "seeds": {"strategy": "paired", "master": 1, "replicates": 2},
        "analysis": {
            "primary_endpoint": "rate_hz",
            "estimand": "paired_diff",
            "uncertainty_method": "bootstrap",
            "multiplicity_policy": "none",
            "exclusion_policy": "none",
            "acceptance_criteria": "unit",
        },
        "resources": {"max_wall_seconds": 10.0, "max_output_bytes": 1000000},
    }
    import yaml

    proto_path.write_text(yaml.safe_dump(proto_doc), encoding="utf-8")
    with pytest.raises(ProtocolValidationError, match="post_neuron_ids"):
        load_and_validate_protocol(proto_path, require_executable=True)


@pytest.mark.unit
def test_compute_windowed_response_metrics_and_failed_run_accounting(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Succeeded run rep 0: 0 pre [0, 0.2), 4 stim [0.2, 0.7), 2 post at 0.75 & 0.85 s
    r0 = runs_dir / "run_ok_0"
    r0.mkdir()
    (r0 / "COMPLETE").write_text("ok", encoding="utf-8")
    (r0 / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_ok_0",
                "condition_id": "disinhib",
                "replicate_id": 0,
                "status": "succeeded",
            }
        ),
        encoding="utf-8",
    )
    pl.DataFrame(
        {
            "run_id": ["run_ok_0"] * 6,
            "condition_id": ["disinhib"] * 6,
            "replicate_id": [0] * 6,
            "source_neuron_id": ["N1"] * 6,
            "spike_time_s": [0.25, 0.35, 0.45, 0.55, 0.75, 0.85],
            "is_synthetic_fixture": [True] * 6,
        }
    ).write_parquet(r0 / "spikes.parquet")

    # Failed run without COMPLETE marker must be accounted transparently
    r_fail = runs_dir / "run_fail_1"
    r_fail.mkdir()
    (r_fail / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_fail_1",
                "condition_id": "disinhib",
                "replicate_id": 1,
                "status": "failed",
                "failure_reason": "synthetic_timeout",
            }
        ),
        encoding="utf-8",
    )

    summary = compute_windowed_response_metrics(
        runs_dir,
        neuron_ids=("N1",),
        pre_window=(0.0, 0.2),
        stim_window=(0.2, 0.7),
        post_window=(0.7, 1.0),
    )

    assert summary["succeeded_run_count"] == 1
    assert summary["failed_run_count"] == 1
    assert summary["failed_runs"][0]["run_id"] == "run_fail_1"

    cond = summary["condition_summaries"]["disinhib"]
    assert cond["pre_rate_hz"]["mean"] == pytest.approx(0.0)
    assert cond["stim_rate_hz"]["mean"] == pytest.approx(4.0 / 0.5)
    assert cond["post_rate_hz"]["mean"] == pytest.approx(2.0 / 0.3)
    assert cond["persistence_duration_s"]["mean"] == pytest.approx(np.float64(0.85 - 0.7))
