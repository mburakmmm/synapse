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
CONFIRMATORY_ROOT = REPO_ROOT / "runs" / "phase5_pain001_confirmatory"
ROBUSTNESS_ROOT = REPO_ROOT / "runs" / "phase5_pain001_robustness"


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


def test_pain001_confirmatory_and_robustness_artifacts_when_present() -> None:
    """Verify confirmatory (120/120) and robustness (36/36) artifacts when present locally."""
    import json

    if not CONFIRMATORY_ROOT.is_dir() or not ROBUSTNESS_ROOT.is_dir():
        pytest.skip("Gitignored local Phase 5A confirmatory/robustness artifacts not present")

    runs_dir = CONFIRMATORY_ROOT / "runs"
    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    assert len(run_dirs) == 120

    sham_count = 0
    for run_dir in run_dirs:
        assert (run_dir / "COMPLETE").is_file()
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "succeeded"
        assert manifest["source_provenance"]["git_dirty"] is False
        if manifest["condition_id"] == "sham_zero_stimulus":
            sham_count += 1
            qc = json.loads((run_dir / "qc.json").read_text(encoding="utf-8"))
            assert qc["total_spikes_in_window"] == 0
    assert sham_count == 15

    summary = json.loads(
        (CONFIRMATORY_ROOT / "confirmatory_summary.json").read_text(encoding="utf-8")
    )
    assert summary["total_runs"] == 120
    assert summary["failed_run_count"] == 0
    assert summary["sham_count"] == 15
    assert summary["sham_max_spikes"] == 0
    assert summary["git_dirty_values"] == [False]
    assert len(summary["primary_contrasts"]) == 6
    assert all(c["bh_fdr_q"] < 0.01 for c in summary["primary_contrasts"])

    for bundle_name in (
        "bundle_523539_edge_mask",
        "bundle_523539_edge_mask_spec",
        "bundle_523539_cell_death",
        "bundle_523539_cell_death_spec",
        "bundle_558778_edge_mask",
        "bundle_558778_edge_mask_spec",
    ):
        bundle_dir = CONFIRMATORY_ROOT / bundle_name
        assert (bundle_dir / "REPRODUCIBILITY.md").is_file()
        assert (bundle_dir / "figures" / "firing_rate_comparison.svg").is_file()

    robust = json.loads((ROBUSTNESS_ROOT / "robustness_summary.json").read_text(encoding="utf-8"))
    assert robust["total_runs"] == 36
    assert robust["failed_run_count"] == 0
    for arm_name in ("shiu_lif", "wsyn_low", "wsyn_high"):
        arm_runs = sorted(p for p in (ROBUSTNESS_ROOT / arm_name / "runs").iterdir() if p.is_dir())
        assert len(arm_runs) == 12
        assert all((p / "COMPLETE").is_file() for p in arm_runs)
        arm = robust["arms"][arm_name]
        assert arm["failed_run_count"] == 0
        assert arm["neurons"]["523539"]["mean_difference_hz"] > 0.0
        assert arm["neurons"]["558778"]["mean_difference_hz"] > 0.0
        assert arm["neurons"]["523539"]["p_value"] == pytest.approx(0.03125)
        assert arm["neurons"]["558778"]["p_value"] == pytest.approx(0.03125)
