"""Phase 5B scientific gate: Sleep/Circadian target set, L3 gates, and L1 pilot artifacts."""

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
    / "sleep"
    / "target_sets"
    / "sleep001_malecns_v1_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-SLEEP-001-pilot.yaml"
CONFIRMATORY_DRAFT_YAML = REPO_ROOT / "research" / "protocols" / "P5-SLEEP-001.yaml"
L3_ROOT = REPO_ROOT / "runs" / "phase5b_sleep001_l3_oscillator"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5b_sleep001_exploratory_pilot"


@pytest.mark.scientific
def test_sleep001_targets_matched_controls_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "malecns_v1_0"
    assert len(targets_doc["metu2a_light_avp"]) == 70
    assert len(targets_doc["ame12_light_clock"]) == 6
    assert len(targets_doc["dn1p_all_clock"]) == 12
    assert len(targets_doc["matched_cb_glut_controls"]) == 12
    assert set(targets_doc["dn1p_all_clock"]).isdisjoint(targets_doc["matched_cb_glut_controls"])
    assert targets_doc["transparency"]["n_controls_edges_to_sleep_clock_readouts"] == 0
    assert targets_doc["transparency"]["n_controls_edges_to_epg"] == 0

    for feat, stats in targets_doc["residual_imbalance"].items():
        assert abs(stats["smd"]) < 0.15, f"Residual imbalance too high for {feat}: {stats['smd']}"

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
def test_sleep001_l3_and_exploratory_pilot_artifacts_when_present() -> None:
    if not L3_ROOT.is_dir() or not (PILOT_ROOT / "runs").is_dir():
        pytest.skip("Gitignored local Phase 5B L3/pilot artifacts not present")

    l3_gate = json.loads((L3_ROOT / "l3_verification_gate.json").read_text(encoding="utf-8"))
    assert l3_gate["overall_passed"] is True
    for g in l3_gate["gates"].values():
        assert g["passed"] is True
    assert (L3_ROOT / "figures" / "l3_prc_curve.svg").is_file()
    assert (L3_ROOT / "figures" / "l3_shift_work_dynamics.svg").is_file()

    l3_sw = json.loads((L3_ROOT / "l3_shift_work_summary.json").read_text(encoding="utf-8"))
    assert set(l3_sw["arms"]) == {
        "ld12_12_control",
        "deprivation_12h_recovery",
        "shift_delay_8h",
        "shift_advance_6h",
        "rotating_shift_8h",
    }
    assert l3_sw["arms"]["rotating_shift_8h"]["days_to_reentrain"] is None

    runs_dir = PILOT_ROOT / "runs"
    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    assert len(run_dirs) == 24

    sham_count = 0
    for rdir in run_dirs:
        assert (rdir / "COMPLETE").is_file()
        manifest = json.loads((rdir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "succeeded"
        assert manifest["is_synthetic_fixture"] is False
        assert manifest["dataset_id"] == "malecns_v1_0"
        assert manifest["protocol_id"] == "P5-SLEEP-001-PILOT"
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
        "bundle_22794_clock_vs_base",
        "bundle_22794_mask_vs_clock",
        "bundle_11886_shift_vs_base",
    ):
        b_dir = PILOT_ROOT / b_name
        assert (b_dir / "REPRODUCIBILITY.md").is_file()
        assert (b_dir / "figures" / "firing_rate_comparison.svg").is_file()
