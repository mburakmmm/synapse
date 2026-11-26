"""Phase 5C-3 scientific gate: Stress L3 allostatic ODEs & MaleCNS L1 pilot."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_core import verify_stress_allostatic_gates
from synapse_experiments import ProtocolValidationError, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_JSON = (
    REPO_ROOT
    / "research"
    / "modules"
    / "stress"
    / "target_sets"
    / "stress001_malecns_v1_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-STRESS-001-pilot.yaml"
CONFIRMATORY_DRAFT_YAML = REPO_ROOT / "research" / "protocols" / "P5-STRESS-001.yaml"
L3_ROOT = REPO_ROOT / "runs" / "phase5c_stress001_l3_allostatic"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5c_stress001_exploratory_pilot"


@pytest.mark.scientific
def test_stress001_targets_l3_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "malecns_v1_0"

    threat = set(targets_doc["threat_sensory_top40"])
    vis_ctrl = set(targets_doc["matched_lc12_visual_controls"])
    inh_gate = set(targets_doc["defensive_inhibitory_gate_top30"])
    inh_ctrl = set(targets_doc["matched_offpathway_inhibitory_controls"])
    assert len(threat) == 40
    assert len(vis_ctrl) == 40
    assert len(inh_gate) == 30
    assert len(inh_ctrl) == 30
    assert targets_doc["transparency"]["disjoint_threat_controls"] is True
    assert targets_doc["transparency"]["disjoint_inh_controls"] is True
    assert targets_doc["transparency"]["zero_control_edges_to_readouts"] is True
    assert targets_doc["matching_quality"]["visual_ctrl_vs_threat40_max_abs_smd"] < 0.20
    assert targets_doc["matching_quality"]["offpathway_inh30_vs_gate30_max_abs_smd"] < 0.20

    gate_report = verify_stress_allostatic_gates()
    assert gate_report["overall_passed"] is True
    assert (
        gate_report["gates"]["post_chronic_washout_and_ruo_guard"]["diagnostic_label_guard_enabled"]
        is True
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
def test_stress001_local_l3_and_l1_pilot_artifacts_when_present() -> None:
    if (
        not (L3_ROOT / "l3_verification_gate.json").is_file()
        or not (PILOT_ROOT / "pilot_summary.json").is_file()
    ):
        pytest.skip("Gitignored local Phase 5C-3 Stress runs/ artifacts absent in CI")

    l3_gate = json.loads((L3_ROOT / "l3_verification_gate.json").read_text(encoding="utf-8"))
    assert l3_gate["overall_passed"] is True
    assert (
        l3_gate["gates"]["chronic_allostatic_overload_separation"]["chronic_vs_acute_load_ratio"]
        > 3.0
    )

    snaps = pl.read_parquet(L3_ROOT / "l3_coupling_snapshots.parquet")
    assert snaps.height == 8

    pilot = json.loads((PILOT_ROOT / "pilot_summary.json").read_text(encoding="utf-8"))
    assert pilot["protocol_id"] == "P5-STRESS-001-PILOT"
    assert pilot["dataset_id"] == "malecns_v1_0"
    assert pilot["succeeded_run_count"] == 24
    assert pilot["failed_run_count"] == 0
    assert pilot["sham_max_spikes"] == 0

    means = pilot["condition_readout_means"]
    acute_p01 = means["acute_threat_baseline_30hz"]["dnp01_escape_mean_hz"]
    depl_p01 = means["chronic_allostatic_reserve_depletion"]["dnp01_escape_mean_hz"]
    sens_p01 = means["chronic_arousal_sensory_sensitization"]["dnp01_escape_mean_hz"]
    ctrl_off_p01 = means["matched_ctrl_offpathway_inh_depletion"]["dnp01_escape_mean_hz"]
    ctrl_vis_p09 = means["matched_ctrl_nondefensive_visual_60hz"]["dnp09_freeze_mean_hz"]
    assert sens_p01 > depl_p01 > acute_p01 > 0.0
    assert abs(ctrl_off_p01 - acute_p01) < 2.0
    assert ctrl_vis_p09 == 0.0
