"""Unit tests for Shiu et al. (2024) LIF fidelity, parallel workers, and benchmark evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from synapse_core import (
    SEED_ALGORITHM,
    Brian2CPUBackend,
    ConstantCurrentStimulus,
    DirectedConnectomeGraph,
    DirectedEdge,
    LIFParameters,
    SeedRecord,
    SimulationRequest,
)
from synapse_data import ingest_synthetic_fixture
from synapse_experiments import (
    evaluate_shiu2024_benchmark,
    load_and_validate_protocol,
    run_protocol_experiment,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_RAW = REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1"
P0_PROTOCOL = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"
P2_PROTOCOL = REPO_ROOT / "research" / "protocols" / "P2-BENCH-SHIU2024.yaml"


@pytest.mark.unit
def test_shiu2024_reference_parameters_and_protocol_valid() -> None:
    p = LIFParameters.shiu2024_reference()
    assert p.model_id == "shiu2024_lif"
    assert p.solver == "linear"
    assert p.dg_unless_refractory is True
    assert p.dt_s == pytest.approx(0.0001)
    assert p.w_syn_v == pytest.approx(0.000275)

    doc, _ = load_and_validate_protocol(P2_PROTOCOL, require_executable=True)
    assert doc["analysis_intent"] == "confirmatory"
    assert doc["model"]["parameter_manifest_sha256"] == p.canonical_sha256()


@pytest.mark.unit
def test_dg_unless_refractory_flag_alters_refractory_synaptic_decay() -> None:
    # PRE fires at t ~ 1.5ms, delivering excitatory impulse while POST is driven into refractory
    g = DirectedConnectomeGraph.from_edges(
        dataset_id="ref_test",
        release="1.0",
        specimen_id="ref0",
        is_synthetic_fixture=True,
        neuron_ids=("PRE", "POST"),
        edges=[DirectedEdge("PRE", "POST", 40)],
        neurotransmitters={"PRE": "ACH", "POST": "ACH"},
    )
    seed_rec = SeedRecord(SEED_ALGORITHM, 0, {"brian2": 1})
    # Drive POST to spike early (~1.9ms) so it is refractory when PRE's spike arrives (~3.6ms)
    interventions = (
        ConstantCurrentStimulus(
            target_neuron_ids=("POST",), current_a=8.0e-9, start_s=0.0, end_s=0.0025
        ),
        ConstantCurrentStimulus(
            target_neuron_ids=("PRE",), current_a=8.0e-9, start_s=0.0, end_s=0.0025
        ),
    )

    p_canonical = LIFParameters(
        t_ref_s=0.010, delay_s=0.002, dt_s=0.0001, dg_unless_refractory=False
    )
    p_shiu = LIFParameters(t_ref_s=0.010, delay_s=0.002, dt_s=0.0001, dg_unless_refractory=True)

    res_canon = Brian2CPUBackend().run(
        SimulationRequest(
            graph=g,
            parameters=p_canonical,
            duration_s=0.025,
            seed_record=seed_rec,
            interventions=interventions,
            record_voltage_neuron_ids=("POST",),
        )
    )
    res_shiu = Brian2CPUBackend().run(
        SimulationRequest(
            graph=g,
            parameters=p_shiu,
            duration_s=0.025,
            seed_record=seed_rec,
            interventions=interventions,
            record_voltage_neuron_ids=("POST",),
        )
    )

    assert res_canon.voltage_traces_v is not None and res_shiu.voltage_traces_v is not None
    # In Brian2, `(unless refractory)` on `dg/dt` gates postsynaptic `on_pre` writes to `g`
    # by `not_refractory`: `shiu2024_lif` drops PRE input during POST's refractory period,
    # whereas canonical `dg_unless_refractory=False` accumulates it and depolarizes POST after.
    post_shiu = res_shiu.voltage_traces_v["POST"][120:]
    post_canon = res_canon.voltage_traces_v["POST"][120:]
    assert np.allclose(post_shiu, p_shiu.v_reset_v)
    assert float(np.max(post_canon)) > float(np.max(post_shiu))


@pytest.mark.unit
def test_parallel_workers_match_serial_and_benchmark_evaluator_gates(tmp_path: Path) -> None:
    ds_dir = tmp_path / "ds"
    ingest_synthetic_fixture(FIXTURE_RAW, ds_dir)

    runs_serial = tmp_path / "runs_serial"
    runs_parallel = tmp_path / "runs_parallel"

    serial_dirs = run_protocol_experiment(
        P0_PROTOCOL, ds_dir, runs_serial, replicates_override=2, repo_root=REPO_ROOT, workers=1
    )
    parallel_dirs = run_protocol_experiment(
        P0_PROTOCOL, ds_dir, runs_parallel, replicates_override=2, repo_root=REPO_ROOT, workers=2
    )
    assert len(serial_dirs) == len(parallel_dirs) == 4

    for sd, pd_dir in zip(serial_dirs, parallel_dirs, strict=True):
        ms = pl.read_parquet(sd / "metrics.parquet").sort("source_neuron_id")
        mp = pl.read_parquet(pd_dir / "metrics.parquet").sort("source_neuron_id")
        assert ms["firing_rate_hz"].to_list() == mp["firing_rate_hz"].to_list()

    # Read observed baseline motor firing rate to verify evaluator PASS and fail-closed FAIL paths
    base_rates = [
        float(
            pl.read_parquet(d / "metrics.parquet").filter(
                pl.col("source_neuron_id") == "9007199254740996"
            )["firing_rate_hz"][0]
        )
        for d in serial_dirs[:2]
    ]
    obs_base_mean = float(np.mean(base_rates))

    ref_pass = tmp_path / "ref_pass.json"
    ref_pass.write_text(
        json.dumps(
            {
                "benchmark_id": "SYNTH-BENCH-TEST",
                "conditions": {
                    "baseline": {
                        "expected_replicates": 2,
                        "expected_max_total_spikes": None,
                        "targets": [
                            {
                                "neuron_id": "9007199254740996",
                                "label": "motor_out",
                                "reference_mean_hz": obs_base_mean,
                                "reference_sd_pop_hz": 0.0,
                                "tolerance_abs_hz": 1.0,
                            }
                        ],
                    }
                },
                "contrasts": [
                    {
                        "contrast_id": "silencing_increases_motor",
                        "baseline_condition": "baseline",
                        "treatment_condition": "inhibitory_silencing",
                        "neuron_id": "9007199254740996",
                        "expected_direction": "positive",
                        "reference_mean_diff_hz": 40.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report_pass_path = evaluate_shiu2024_benchmark(
        runs_parallel, ref_pass, tmp_path / "eval_pass", expected_replicates_override=2
    )
    assert json.loads(report_pass_path.read_text(encoding="utf-8"))["overall_passed"] is True

    # Tight impossible reference value must fail overall_passed honestly
    ref_fail = tmp_path / "ref_fail.json"
    ref_data = json.loads(ref_pass.read_text(encoding="utf-8"))
    ref_data["conditions"]["baseline"]["targets"][0]["reference_mean_hz"] = obs_base_mean + 50.0
    ref_fail.write_text(json.dumps(ref_data), encoding="utf-8")
    report_fail_path = evaluate_shiu2024_benchmark(
        runs_parallel, ref_fail, tmp_path / "eval_fail", expected_replicates_override=2
    )
    assert json.loads(report_fail_path.read_text(encoding="utf-8"))["overall_passed"] is False
