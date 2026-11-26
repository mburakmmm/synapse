"""Phase 5C scientific gate: Neuro L0 topology/ablation, MaleCNS L0 audit & L1 FlyWire pilot."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_experiments import ProtocolValidationError, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_JSON = (
    REPO_ROOT
    / "research"
    / "modules"
    / "neuro"
    / "target_sets"
    / "neuro001_flywire_v630_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-NEURO-001-pilot.yaml"
CONFIRMATORY_DRAFT_YAML = REPO_ROOT / "research" / "protocols" / "P5-NEURO-001.yaml"
L0_ROOT = REPO_ROOT / "runs" / "phase5c_neuro001_l0_topology"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5c_neuro001_exploratory_pilot"


@pytest.mark.scientific
def test_neuro001_targets_matched_controls_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "flywire_fafb_v630"

    grns = set(targets_doc["source_sugar_grn_ids"])
    hubs = set(targets_doc["targeted_premotor_hub_ids"])
    ctrl_cells = set(targets_doc["matched_control_neuron_ids"])
    mn9 = set(targets_doc["readout_mn9_ids"])
    assert len(grns) == 21
    assert len(hubs) == 12
    assert len(ctrl_cells) == 12
    assert len(mn9) == 2
    assert targets_doc["transparency"]["disjoint_grn_hubs_ctrl"] is True
    assert targets_doc["transparency"]["disjoint_ctrl_syn_from_feeding_core"] is True
    assert targets_doc["transparency"]["max_abs_cell_control_smd"] < 0.20

    tgt_syn = targets_doc["targeted_synapse_ablation"]
    ctrl_syn = targets_doc["matched_control_synapse_ablation"]
    assert tgt_syn["exact_cartesian_edge_count"] == 22
    assert tgt_syn["exact_synapse_count"] == 3170
    assert 20 <= ctrl_syn["exact_cartesian_edge_count"] <= 24
    assert abs(ctrl_syn["rel_synapse_diff_vs_targeted"]) <= 0.05

    pilot_doc, _ = load_and_validate_protocol(PILOT_YAML, require_executable=True)
    assert pilot_doc["analysis_intent"] == "exploratory"
    assert int(pilot_doc["seeds"]["replicates"]) == 3
    assert len(pilot_doc["conditions"]) == 8

    # Draft confirmatory protocol must pass JSON Schema yet stay blocked until human freeze
    conf_doc, _ = load_and_validate_protocol(CONFIRMATORY_DRAFT_YAML, require_executable=False)
    assert conf_doc["status"] == "draft"
    assert conf_doc["analysis_intent"] == "confirmatory"
    assert int(conf_doc["seeds"]["replicates"]) == 15
    with pytest.raises(ProtocolValidationError, match="approved"):
        load_and_validate_protocol(CONFIRMATORY_DRAFT_YAML, require_executable=True)


@pytest.mark.scientific
def test_neuro001_l0_and_exploratory_pilot_artifacts_when_present() -> None:
    if not L0_ROOT.is_dir() or not (PILOT_ROOT / "runs").is_dir():
        pytest.skip("Gitignored local Phase 5C Neuro L0/pilot artifacts not present")

    l0_gate = json.loads((L0_ROOT / "l0_verification_gate.json").read_text(encoding="utf-8"))
    assert l0_gate["overall_passed"] is True
    for g in l0_gate["gates"].values():
        assert g["passed"] is True
    assert (L0_ROOT / "figures" / "l0_attack_curve.svg").is_file()
    assert (L0_ROOT / "figures" / "l0_ablation_dissociation.svg").is_file()

    l0_sum = json.loads((L0_ROOT / "l0_ablation_summary.json").read_text(encoding="utf-8"))
    k12_tgt = next(
        p
        for p in l0_sum["curve_points"]
        if p["arm_type"] == "targeted_cell_loss" and p["step_k"] == 12
    )
    k12_ctrl = next(
        p
        for p in l0_sum["curve_points"]
        if p["arm_type"] == "matched_random_cell_loss" and p["step_k"] == 12
    )
    assert k12_tgt["weighted_eff_ratio"] < 0.70
    assert k12_tgt["three_hop_flow_ratio"] < 0.15
    assert k12_ctrl["weighted_eff_ratio"] == pytest.approx(1.0)
    assert k12_ctrl["three_hop_flow_ratio"] == pytest.approx(1.0)

    malecns_audit = json.loads(
        (L0_ROOT / "malecns_l0_structural_audit.json").read_text(encoding="utf-8")
    )
    assert malecns_audit["dataset_id"] == "malecns_v1_0"
    assert malecns_audit["matched_control_max_abs_smd"] < 0.15

    runs_dir = PILOT_ROOT / "runs"
    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    assert len(run_dirs) == 24

    sham_count = 0
    for rdir in run_dirs:
        assert (rdir / "COMPLETE").is_file()
        manifest = json.loads((rdir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "succeeded"
        assert manifest["is_synthetic_fixture"] is False
        assert manifest["dataset_id"] == "flywire_fafb_v630"
        assert manifest["protocol_id"] == "P5-NEURO-001-PILOT"
        if manifest["condition_id"] == "sham_zero_stimulus":
            sham_count += 1
            df = pl.read_parquet(rdir / "metrics.parquet")
            assert int(df["spike_count"].sum()) == 0
    assert sham_count == 3

    ps = json.loads((PILOT_ROOT / "pilot_summary.json").read_text(encoding="utf-8"))
    assert ps["total_runs"] == 24
    assert ps["failed_run_count"] == 0
    assert ps["sham_max_spikes"] == 0

    for b_name in (
        "bundle_mn9r_cell_loss_top12_vs_intact",
        "bundle_mn9r_cell_loss_vs_matched_ctrl",
        "bundle_mn9r_cell_vs_synapse_dissociation",
    ):
        b_dir = PILOT_ROOT / b_name
        assert (b_dir / "REPRODUCIBILITY.md").is_file()
        assert (b_dir / "figures" / "firing_rate_comparison.svg").is_file()
