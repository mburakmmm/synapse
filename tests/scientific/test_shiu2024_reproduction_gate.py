"""Phase 2 scientific gate verifying real Shiu et al. (2024) reproduction artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPORT_PATH = Path("runs/phase2_shiu2024_reproduction_r2/evaluation/benchmark_report.json")
_ANALYSIS_MANIFEST_PATH = Path(
    "runs/phase2_shiu2024_reproduction_r2/analysis_mn9/analysis_manifest.json"
)
_REPRO_DOC_PATH = Path("runs/phase2_shiu2024_reproduction_r2/bundle_mn9/REPRODUCIBILITY.md")


@pytest.mark.scientific
def test_shiu2024_reproduction_gate() -> None:
    if not _REPORT_PATH.is_file():
        pytest.skip(f"Local gitignored Phase 2 reproduction artifacts not present: {_REPORT_PATH}")

    report = json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    assert report["overall_passed"] is True
    assert report["failed_run_count"] == 0

    prov = report["provenance"]
    assert prov["is_synthetic_fixture"] is False
    assert prov["dataset_id"] == "flywire_fafb_v630"
    assert prov["model_id"] == "shiu2024_lif"

    assert report["condition_replicate_counts"] == {
        "baseline_no_stimulus": {
            "expected_replicates": 30,
            "observed_replicates": 30,
            "passed": True,
        },
        "sugar_grn_100hz": {
            "expected_replicates": 30,
            "observed_replicates": 30,
            "passed": True,
        },
        "sugar_grn_100hz_silence_grn15": {
            "expected_replicates": 30,
            "observed_replicates": 30,
            "passed": True,
        },
    }

    assert report["spike_control_checks"]
    assert all(check["passed"] is True for check in report["spike_control_checks"])
    assert report["target_comparisons"]
    assert all(comp["passed"] is True for comp in report["target_comparisons"])
    assert report["contrast_comparisons"]
    assert all(comp["passed"] is True for comp in report["contrast_comparisons"])

    assert _ANALYSIS_MANIFEST_PATH.is_file()
    analysis = json.loads(_ANALYSIS_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert analysis["failed_run_count"] == 0
    assert analysis["provenance"]["is_synthetic_fixture"] is False
    assert analysis["paired_metrics"]["n_pairs"] == 30
    assert analysis["paired_metrics"]["mean_difference_hz"] < 0.0

    assert _REPRO_DOC_PATH.is_file()
