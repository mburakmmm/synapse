"""Phase 4 scientific gates: frozen MET-001 protocol/controls, confirmatory runs, and robustness."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_analysis import bh_fdr_adjust
from synapse_experiments import ProtocolValidationError, freeze_protocol, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_JSON = (
    REPO_ROOT
    / "research"
    / "modules"
    / "metabolic"
    / "target_sets"
    / "met001_flywire_v630_targets.json"
)
PILOT_YAML = REPO_ROOT / "research" / "protocols" / "P4-MET-001-pilot.yaml"
APPROVED_YAML = REPO_ROOT / "research" / "protocols" / "P4-MET-001.yaml"
FROZEN_YAML = REPO_ROOT / "research" / "protocols" / "P4-MET-001.frozen.yaml"
PILOT_RUNS_ROOT = REPO_ROOT / "runs" / "phase4_met001_exploratory_pilot"
CONFIRMATORY_ROOT = REPO_ROOT / "runs" / "phase4_met001_confirmatory"
ROBUSTNESS_ROOT = REPO_ROOT / "runs" / "phase4_met001_robustness"


@pytest.mark.scientific
def test_met001_targets_and_frozen_protocol_gate() -> None:
    targets_doc = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    assert targets_doc["source_dataset_id"] == "flywire_fafb_v630"
    assert len(targets_doc["target_neuron_ids"]) == 21
    assert len(targets_doc["control_neuron_ids"]) == 21
    assert set(targets_doc["target_neuron_ids"]).isdisjoint(targets_doc["control_neuron_ids"])

    for feat, stats in targets_doc["residual_imbalance"].items():
        assert abs(stats["smd"]) < 0.15, f"Residual imbalance too high for {feat}: {stats['smd']}"

    pilot_doc, _ = load_and_validate_protocol(PILOT_YAML, require_executable=True)
    assert pilot_doc["analysis_intent"] == "exploratory"

    approved_doc, _ = load_and_validate_protocol(APPROVED_YAML, require_executable=True)
    assert approved_doc["status"] == "approved"
    assert approved_doc["analysis_intent"] == "confirmatory"

    frozen_doc, frozen_sha = load_and_validate_protocol(FROZEN_YAML, require_executable=True)
    assert frozen_doc["status"] == "frozen"
    assert frozen_doc["analysis_intent"] == "confirmatory"
    assert int(frozen_doc["seeds"]["replicates"]) == 30
    assert frozen_sha == "d15ad4aafe1088fa1bc6afb62b58528b27e948c1f2d07c3484963eebb00bef05"

    # Frozen revision must remain immutable
    with pytest.raises(ProtocolValidationError, match="Refusing to overwrite"):
        freeze_protocol(APPROVED_YAML, out_path=FROZEN_YAML, confirmed=True)


@pytest.mark.scientific
def test_met001_exploratory_pilot_artifacts_when_present() -> None:
    runs_dir = PILOT_RUNS_ROOT / "runs"
    if not runs_dir.is_dir():
        pytest.skip(f"Local gitignored Phase 4 pilot artifacts not present: {runs_dir}")

    manifests = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir.rglob("manifest.json"))
    ]
    assert len(manifests) == 15
    for m in manifests:
        assert m["status"] == "succeeded"
        assert m["is_synthetic_fixture"] is False
        assert m["analysis_intent"] == "exploratory"
        assert m["protocol_id"] == "P4-MET-001-PILOT"
        if m["condition_id"] == "sham_zero_stimulus":
            df = pl.read_parquet(runs_dir / m["run_id"] / "metrics.parquet")
            assert int(df["spike_count"].sum()) == 0

    for subdir in ("analysis_gain_1p50", "analysis_specificity"):
        am = json.loads((PILOT_RUNS_ROOT / subdir / "analysis_manifest.json").read_text("utf-8"))
        assert am["failed_run_count"] == 0
        assert am["provenance"]["is_synthetic_fixture"] is False
        assert am["provenance"]["analysis_intent"] == "exploratory"
        assert am["paired_metrics"]["n_pairs"] == 3


@pytest.mark.scientific
def test_met001_confirmatory_and_robustness_artifacts_when_present() -> None:
    runs_dir = CONFIRMATORY_ROOT / "runs"
    if not runs_dir.is_dir():
        pytest.skip(f"Local gitignored Phase 4 confirmatory artifacts not present: {runs_dir}")

    manifests = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir.rglob("manifest.json"))
    ]
    assert len(manifests) == 180
    sham_count = 0
    for m in manifests:
        assert m["status"] == "succeeded"
        assert (runs_dir / m["run_id"] / "COMPLETE").is_file()
        assert m["is_synthetic_fixture"] is False
        assert m["analysis_intent"] == "confirmatory"
        assert m["protocol_id"] == "P4-MET-001"
        if m["condition_id"] == "sham_zero_stimulus":
            sham_count += 1
            df = pl.read_parquet(runs_dir / m["run_id"] / "metrics.parquet")
            assert int(df["spike_count"].sum()) == 0
    assert sham_count == 30

    pvals = []
    contrasts = ("analysis_mn9r_gain_1p50", "analysis_mn9r_specificity", "analysis_mn9r_gain_1p25")
    for subdir in contrasts:
        am = json.loads((CONFIRMATORY_ROOT / subdir / "analysis_manifest.json").read_text("utf-8"))
        assert am["failed_run_count"] == 0
        assert am["provenance"]["is_synthetic_fixture"] is False
        assert am["provenance"]["analysis_intent"] == "confirmatory"
        assert am["paired_metrics"]["n_pairs"] == 30
        pvals.append(float(am["paired_metrics"]["permutation_test"]["two_sided_p_value"]))
    assert all(q < 0.01 for q in bh_fdr_adjust(pvals))

    assert (
        CONFIRMATORY_ROOT / "bundle_mn9r_gain_1p50" / "figures" / "firing_rate_comparison.svg"
    ).is_file()
    assert (CONFIRMATORY_ROOT / "bundle_mn9r_specificity" / "REPRODUCIBILITY.md").is_file()

    if ROBUSTNESS_ROOT.is_dir():
        for arm in ("canonical_lif", "wsyn_low", "wsyn_high"):
            arm_runs = [
                json.loads(p.read_text(encoding="utf-8"))
                for p in sorted((ROBUSTNESS_ROOT / arm / "runs").rglob("manifest.json"))
            ]
            assert len(arm_runs) == 12
            assert all(r["status"] == "succeeded" for r in arm_runs)
            arm_am = json.loads(
                (ROBUSTNESS_ROOT / arm / "analysis_mn9r" / "analysis_manifest.json").read_text(
                    "utf-8"
                )
            )
            assert arm_am["failed_run_count"] == 0
            assert arm_am["paired_metrics"]["n_pairs"] == 6
