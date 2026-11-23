"""Phase 5B scientific gate: Addiction MB plasticity, target set, and L1 pilot artifacts."""

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
    / "addiction"
    / "target_sets"
    / "add001_malecns_v1_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-ADD-001-pilot.yaml"
CONFIRMATORY_DRAFT_YAML = REPO_ROOT / "research" / "protocols" / "P5-ADD-001.yaml"
L2_ROOT = REPO_ROOT / "runs" / "phase5b_add001_l2_plasticity"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5b_add001_exploratory_pilot"


@pytest.mark.scientific
def test_add001_targets_matched_controls_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "malecns_v1_0"

    cs_plus = set(targets_doc["cs_plus_kcs"])
    matched_ctrl = set(targets_doc["matched_ctrl_kcs"])
    cs_minus = set(targets_doc["cs_minus_kcs"])
    assert len(cs_plus) == 143
    assert len(matched_ctrl) == 143
    assert len(cs_minus) == 143
    assert cs_plus.isdisjoint(matched_ctrl)
    assert cs_plus.isdisjoint(cs_minus)
    assert matched_ctrl.isdisjoint(cs_minus)

    assert targets_doc["transparency"]["disjoint_sets"] is True
    assert targets_doc["transparency"]["n_ctrl_pn_a_syn"] == 0
    assert targets_doc["transparency"]["n_ctrl_pn_b_syn"] == 0

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
def test_add001_l2_and_exploratory_pilot_artifacts_when_present() -> None:
    if not L2_ROOT.is_dir() or not (PILOT_ROOT / "runs").is_dir():
        pytest.skip("Gitignored local Phase 5B Addiction L2/pilot artifacts not present")

    l2_gate = json.loads((L2_ROOT / "l2_verification_gate.json").read_text(encoding="utf-8"))
    assert l2_gate["overall_passed"] is True
    for g in l2_gate["gates"].values():
        assert g["passed"] is True
    assert (L2_ROOT / "figures" / "l2_controls_comparison.svg").is_file()
    assert (L2_ROOT / "figures" / "l2_learning_curve.svg").is_file()

    l2_par = json.loads((L2_ROOT / "l2_paradigm_summary.json").read_text(encoding="utf-8"))
    assert set(l2_par["arms"]) == {
        "paired_conditioning",
        "spontaneous_recovery_only",
        "yoked_unpaired",
        "sham_no_stimulus",
        "dan_blocked",
    }

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
        assert manifest["protocol_id"] == "P5-ADD-001-PILOT"
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
        "bundle_mbon02_acq_vs_naive",
        "bundle_mbon14_acq_vs_naive",
        "bundle_mbon18_reinst_vs_ext",
    ):
        b_dir = PILOT_ROOT / b_name
        assert (b_dir / "REPRODUCIBILITY.md").is_file()
        assert (b_dir / "figures" / "firing_rate_comparison.svg").is_file()
