"""End-to-end Phase 0 vertical slice integration and CLI verification tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import polars as pl
import pytest

from synapse_analysis import run_paired_analysis, sha256_file
from synapse_cli.main import main as cli_main
from synapse_data import DataGateError, ingest_synthetic_fixture
from synapse_experiments import (
    load_graph_from_dataset,
    run_protocol_experiment,
    validate_run_manifest_schema,
)
from synapse_publication import export_evidence_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_RAW = REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1"
P0_PROTOCOL = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"


@pytest.mark.integration
def test_corrupt_fixture_quarantines_and_fails_closed(tmp_path: Path) -> None:
    bad_raw = tmp_path / "bad_raw"
    shutil.copytree(FIXTURE_RAW, bad_raw)
    # Append invalid connection with non-positive synapse count and unknown target ID
    conn_file = bad_raw / "connections.csv"
    conn_file.write_text(
        conn_file.read_text(encoding="utf-8")
        + "9007199254740993,9999999999999999,-5,synthetic_core,1.0,sum\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "bad_dataset"
    with pytest.raises(DataGateError, match="quarantined 1 invalid record"):
        ingest_synthetic_fixture(bad_raw, out_dir)

    q_df = pl.read_parquet(out_dir / "quarantine.parquet")
    assert q_df.height == 1
    assert q_df["table"][0] == "connections"


@pytest.mark.integration
def test_phase0_end_to_end_vertical_slice_determinism_and_failed_run_accounting(
    tmp_path: Path,
) -> None:
    dataset_dir = tmp_path / "dataset"
    manifest_path = ingest_synthetic_fixture(FIXTURE_RAW, dataset_dir)
    assert manifest_path.is_file()

    graph, ds_manifest, _ = load_graph_from_dataset(dataset_dir)
    assert graph.is_synthetic_fixture is True
    assert ds_manifest["is_synthetic_fixture"] is True
    assert graph.n_neurons == 4
    assert graph.n_edges == 4
    assert "9007199254740996" in graph.neuron_ids

    runs_a = tmp_path / "runs_a"
    run_dirs_a = run_protocol_experiment(
        P0_PROTOCOL, dataset_dir, runs_a, replicates_override=3, repo_root=REPO_ROOT
    )
    assert len(run_dirs_a) == 6  # 2 conditions * 3 paired seeds

    for rdir in run_dirs_a:
        assert (rdir / "COMPLETE").is_file()
        manifest = json.loads((rdir / "manifest.json").read_text(encoding="utf-8"))
        validate_run_manifest_schema(manifest)
        assert manifest["status"] == "succeeded"
        assert manifest["is_synthetic_fixture"] is True

    # Replay determinism check with a fresh runs directory
    runs_b = tmp_path / "runs_b"
    run_dirs_b = run_protocol_experiment(
        P0_PROTOCOL, dataset_dir, runs_b, replicates_override=3, repo_root=REPO_ROOT
    )
    for ra, rb in zip(run_dirs_a, run_dirs_b, strict=True):
        ma = pl.read_parquet(ra / "metrics.parquet").sort("source_neuron_id")
        mb = pl.read_parquet(rb / "metrics.parquet").sort("source_neuron_id")
        assert ma["firing_rate_hz"].to_list() == mb["firing_rate_hz"].to_list()
        sa = pl.read_parquet(ra / "spikes.parquet")
        sb = pl.read_parquet(rb / "spikes.parquet")
        assert sa["spike_time_s"].to_list() == sb["spike_time_s"].to_list()

    # Inject a failed run into runs_a to verify transparent failed-run accounting
    failed_dir = runs_a / "P0-SYNTH-001_baseline_rep999_failedtest"
    failed_dir.mkdir(parents=True)
    (failed_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "P0-SYNTH-001_baseline_rep999_failedtest",
                "status": "failed",
                "condition_id": "baseline",
                "replicate_id": 999,
                "failure_reason": "Simulated worker crash test",
            }
        ),
        encoding="utf-8",
    )

    analysis_dir = tmp_path / "analysis"
    analysis_manifest_path = run_paired_analysis(
        runs_dir=runs_a,
        out_dir=analysis_dir,
        baseline_condition="baseline",
        treatment_condition="inhibitory_silencing",
        target_neuron_id="9007199254740996",
    )
    analysis_manifest = json.loads(analysis_manifest_path.read_text(encoding="utf-8"))
    assert analysis_manifest["failed_run_count"] == 1
    assert (
        analysis_manifest["failed_runs"][0]["run_id"] == "P0-SYNTH-001_baseline_rep999_failedtest"
    )
    # Silencing GABAergic interneuron must increase downstream motor firing rate
    assert analysis_manifest["paired_metrics"]["mean_difference_hz"] > 0.0

    bundle_dir = tmp_path / "bundle"
    bundle_manifest_path = export_evidence_bundle(analysis_dir=analysis_dir, out_dir=bundle_dir)
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    assert bundle_manifest["is_synthetic_fixture"] is True
    assert bundle_manifest["failed_run_count"] == 1

    # Verify every exported file checksum and non-empty figure artifacts
    for entry in bundle_manifest["files"]:
        f_path = bundle_dir / entry["path"]
        assert f_path.is_file() and f_path.stat().st_size > 0
        assert sha256_file(f_path) == entry["sha256"]

    # Verify figure source table equals paired_differences.parquet 1-to-1
    paired_df = pl.read_parquet(analysis_dir / "paired_differences.parquet")
    fig_table_df = pl.read_csv(
        bundle_dir / "tables" / "figure1_source_data.csv",
        schema_overrides={"target_neuron_id": pl.String},
    )
    b_rows = fig_table_df.filter(pl.col("condition_id") == "baseline").sort("replicate_id")
    t_rows = fig_table_df.filter(pl.col("condition_id") == "inhibitory_silencing").sort(
        "replicate_id"
    )
    assert b_rows["firing_rate_hz"].to_list() == pytest.approx(
        paired_df.sort("replicate_id")["baseline_rate_hz"].to_list()
    )
    assert t_rows["firing_rate_hz"].to_list() == pytest.approx(
        paired_df.sort("replicate_id")["treatment_rate_hz"].to_list()
    )

    repro_text = (bundle_dir / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "SYNTHETIC ENGINEERING FIXTURE" in repro_text
    assert "P0-SYNTH-001_baseline_rep999_failedtest" in repro_text


@pytest.mark.integration
def test_cli_smoke_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main(["doctor", "--json"]) == 0
    doc_out = json.loads(capsys.readouterr().out)
    assert doc_out["status"] == "ok"

    assert cli_main(["dataset", "plan", "flywire_fafb_v630", "--json"]) == 0
    plan_out = json.loads(capsys.readouterr().out)
    assert plan_out["approval_required"] is True

    assert cli_main(["protocol", "validate", str(P0_PROTOCOL), "--json"]) == 0
    capsys.readouterr()

    draft_path = REPO_ROOT / "research" / "protocols" / "P1-BENCH-SHIU2024-draft.yaml"
    assert cli_main(["protocol", "validate", str(draft_path)]) == 2
    capsys.readouterr()

    work_dir = tmp_path / "cli_demo"
    assert (
        cli_main(["run", "synthetic-demo", "--work-dir", str(work_dir), "--seeds", "2", "--json"])
        == 0
    )
    demo_out = json.loads(capsys.readouterr().out)
    assert demo_out["n_runs_completed"] == 4
    assert demo_out["is_synthetic_fixture"] is True
    assert demo_out["paired_metrics"]["mean_difference_hz"] > 0.0
