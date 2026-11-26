"""Phase 5C-2 scientific gate: Pharma L2 receptor kinetics & MaleCNS L1 pilot."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_core import verify_pharmacology_gates
from synapse_experiments import ProtocolValidationError, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_JSON = (
    REPO_ROOT
    / "research"
    / "modules"
    / "pharma"
    / "target_sets"
    / "pharma001_malecns_v1_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-PHARMA-001-pilot.yaml"
CONFIRMATORY_DRAFT_YAML = REPO_ROOT / "research" / "protocols" / "P5-PHARMA-001.yaml"
L2_ROOT = REPO_ROOT / "runs" / "phase5c_pharma001_l2_kinetics"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5c_pharma001_exploratory_pilot"


@pytest.mark.scientific
def test_pharma001_targets_kinetics_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "malecns_v1_0"

    ach = set(targets_doc["sensory_nachr_ach_targets"])
    rdl = set(targets_doc["rdl_gaba_feedforward_targets"])
    ctrl = set(targets_doc["matched_vnc_gaba_controls"])
    asc = set(targets_doc["ascending_readout_all"])
    assert len(ach) == 30
    assert len(rdl) == 26
    assert len(ctrl) == 26
    assert len(asc) == 6
    assert ach.isdisjoint(rdl)
    assert rdl.isdisjoint(ctrl)
    assert (
        targets_doc["receptor_model_mapping"]["matched_vnc_gaba_controls"][
            "edge_count_to_ascending_all"
        ]
        == 0
    )

    gate_report = verify_pharmacology_gates()
    assert gate_report["overall_passed"] is True
    assert (
        gate_report["gates"]["ruo_dose_independent_guard"]["named_compound_gate_enabled"] is False
    )

    pilot_doc, _ = load_and_validate_protocol(PILOT_YAML, require_executable=True)
    assert pilot_doc["analysis_intent"] == "exploratory"
    assert int(pilot_doc["seeds"]["replicates"]) == 3
    assert len(pilot_doc["conditions"]) == 8

    # Draft confirmatory protocol validates structurally yet fails strict execution gate
    conf_doc, _ = load_and_validate_protocol(CONFIRMATORY_DRAFT_YAML, require_executable=False)
    assert conf_doc["status"] == "draft"
    assert conf_doc["analysis_intent"] == "confirmatory"
    assert int(conf_doc["seeds"]["replicates"]) == 15
    with pytest.raises(ProtocolValidationError, match="approved"):
        load_and_validate_protocol(CONFIRMATORY_DRAFT_YAML, require_executable=True)


@pytest.mark.scientific
def test_pharma001_local_l2_and_l1_pilot_artifacts_when_present() -> None:
    if (
        not (L2_ROOT / "l2_verification_gate.json").is_file()
        or not (PILOT_ROOT / "pilot_summary.json").is_file()
    ):
        pytest.skip("Gitignored local Phase 5C-2 Pharma runs/ artifacts absent in CI")

    l2_gate = json.loads((L2_ROOT / "l2_verification_gate.json").read_text(encoding="utf-8"))
    assert l2_gate["overall_passed"] is True
    assert abs(l2_gate["gates"]["schild_linearity_and_slope"]["schild_slope"] - 1.0) < 1e-6

    snaps = pl.read_parquet(L2_ROOT / "l2_coupling_snapshots.parquet")
    assert snaps.height == 8

    pilot = json.loads((PILOT_ROOT / "pilot_summary.json").read_text(encoding="utf-8"))
    assert pilot["protocol_id"] == "P5-PHARMA-001-PILOT"
    assert pilot["dataset_id"] == "malecns_v1_0"
    assert pilot["succeeded_run_count"] == 24
    assert pilot["failed_run_count"] == 0
    assert pilot["sham_max_spikes"] == 0

    means = pilot["condition_readout_means"]
    veh = means["vehicle_baseline_40hz"]["anxxx027_l_523539_mean_hz"]
    antag = means["rdl_gaba_antag_100pct"]["anxxx027_l_523539_mean_hz"]
    pam = means["rdl_gaba_pam_175pct"]["anxxx027_l_523539_mean_hz"]
    comb = means["combined_rdl_pam_plus_nachr_atten"]["anxxx027_l_523539_mean_hz"]
    ctrl = means["matched_ctrl_rdl_antag_100pct"]["anxxx027_l_523539_mean_hz"]
    assert antag > veh > pam > comb > 0.0
    assert abs(ctrl - veh) < 2.0
