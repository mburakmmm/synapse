"""Phase 5A scientific gate: Pain target/control invariants, protocol gates, and pilot artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_experiments import ProtocolValidationError, freeze_protocol, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_JSON = (
    REPO_ROOT / "research" / "modules" / "pain" / "target_sets" / "pain001_malecns_v1_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P5-PAIN-001-pilot.yaml"
CONFIRMATORY_APPROVED_YAML = REPO_ROOT / "research" / "protocols" / "P5-PAIN-001.yaml"
CONFIRMATORY_FROZEN_YAML = REPO_ROOT / "research" / "protocols" / "P5-PAIN-001.frozen.yaml"
PILOT_ROOT = REPO_ROOT / "runs" / "phase5_pain001_exploratory_pilot"


@pytest.mark.scientific
def test_pain001_targets_matched_controls_and_protocol_gates() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "malecns_v1_0"
    assert len(targets_doc["sensory_mesoln_r_tactile_top30"]) == 30
    assert len(targets_doc["gaba_feedforward_targets"]) == 26
    assert len(targets_doc["matched_vnc_gaba_controls"]) == 26
    assert set(targets_doc["gaba_feedforward_targets"]).isdisjoint(
        targets_doc["matched_vnc_gaba_controls"]
    )
    assert targets_doc["transparency"]["n_controls_direct_to_ascending_all"] == 0

    for feat, stats in targets_doc["residual_imbalance"].items():
        assert abs(stats["smd"]) < 0.15, f"Residual imbalance too high for {feat}: {stats['smd']}"

    pilot_doc, _ = load_and_validate_protocol(PILOT_YAML, require_executable=True)
    assert pilot_doc["analysis_intent"] == "exploratory"
    assert int(pilot_doc["seeds"]["replicates"]) == 3
    assert len(pilot_doc["conditions"]) == 8

    approved_doc, _ = load_and_validate_protocol(
        CONFIRMATORY_APPROVED_YAML, require_executable=True
    )
    assert approved_doc["status"] == "approved"
    assert approved_doc["analysis_intent"] == "confirmatory"

    frozen_doc, frozen_sha = load_and_validate_protocol(
        CONFIRMATORY_FROZEN_YAML, require_executable=True
    )
    assert frozen_doc["status"] == "frozen"
    assert frozen_doc["analysis_intent"] == "confirmatory"
    assert int(frozen_doc["seeds"]["replicates"]) == 15
    assert frozen_sha == "a379c7e1c7b264859fe777730464cd8d34807dc1772818b5c4bb4b978ed683cf"

    # Frozen confirmatory revision must remain immutable
    with pytest.raises(ProtocolValidationError, match="Refusing to overwrite"):
        freeze_protocol(
            CONFIRMATORY_APPROVED_YAML,
            out_path=CONFIRMATORY_FROZEN_YAML,
            confirmed=True,
        )


@pytest.mark.scientific
def test_pain001_exploratory_pilot_artifacts_when_present() -> None:
    runs_dir = PILOT_ROOT / "runs"
    if not runs_dir.is_dir():
        pytest.skip(f"Local gitignored Phase 5 Pain pilot artifacts not present: {runs_dir}")

    manifests = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir.rglob("manifest.json"))
    ]
    assert len(manifests) == 24
    sham_count = 0
    for m in manifests:
        assert m["status"] == "succeeded"
        assert (runs_dir / m["run_id"] / "COMPLETE").is_file()
        assert m["is_synthetic_fixture"] is False
        assert m["dataset_id"] == "malecns_v1_0"
        assert m["analysis_intent"] == "exploratory"
        assert m["protocol_id"] == "P5-PAIN-001-PILOT"
        if m["condition_id"] == "sham_zero_stimulus":
            sham_count += 1
            df = pl.read_parquet(runs_dir / m["run_id"] / "metrics.parquet")
            assert int(df["spike_count"].sum()) == 0
    assert sham_count == 3

    win = json.loads((PILOT_ROOT / "windowed_summary.json").read_text(encoding="utf-8"))
    assert win["succeeded_run_count"] == 24
    assert win["failed_run_count"] == 0
    per_n = win["per_neuron_condition_summaries"]
    rate_523539_base = per_n["mesoln_40hz_baseline"]["523539"]["stim_rate_hz"]["mean"]
    rate_523539_mask = per_n["mesoln_40hz_acute_edge_mask"]["523539"]["stim_rate_hz"]["mean"]
    rate_523539_death = per_n["mesoln_40hz_gaba_cell_death"]["523539"]["stim_rate_hz"]["mean"]
    rate_523539_ctrl = per_n["mesoln_40hz_matched_ctrl_ablation"]["523539"]["stim_rate_hz"]["mean"]
    assert rate_523539_mask > rate_523539_base
    assert rate_523539_death > rate_523539_ctrl

    assert (
        PILOT_ROOT / "bundle_523539_anxxx027l_40hz_edge_mask_vs_base" / "REPRODUCIBILITY.md"
    ).is_file()
    assert (
        PILOT_ROOT
        / "bundle_523539_anxxx027l_40hz_edge_mask_vs_base"
        / "figures"
        / "firing_rate_comparison.svg"
    ).is_file()
