"""Integration tests for CLI Phase 3 lifecycle: model validate, freeze, plan, start, cancel."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import yaml

from synapse_cli.main import main as cli_main
from synapse_core import LIFParameters
from synapse_data import ingest_synthetic_fixture

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTH_RAW = REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1"
P0_SYNTH = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"


@pytest.mark.integration
def test_cli_model_validate_protocol_freeze_and_run_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model_file = tmp_path / "model.yaml"
    ref = LIFParameters.shiu2024_reference()
    model_file.write_text(
        yaml.safe_dump(
            {
                "id": ref.model_id,
                "revision": ref.model_revision,
                "backend": "brian2_cpu",
                "parameter_manifest_sha256": ref.canonical_sha256(),
                "parameters": ref.model_dump(mode="json"),
            }
        ),
        encoding="utf-8",
    )
    assert cli_main(["model", "validate", str(model_file), "--json"]) == 0
    val_out = json.loads(capsys.readouterr().out)
    assert val_out["valid"] is True
    assert val_out["gpu_verified"] is False

    # Freeze fails closed without --confirm-freeze
    frozen_out = tmp_path / "p0.frozen.yaml"
    assert cli_main(["protocol", "freeze", str(P0_SYNTH), "--out", str(frozen_out)]) == 2
    capsys.readouterr()

    # Freeze succeeds with deliberate human confirmation
    assert (
        cli_main(
            [
                "protocol",
                "freeze",
                str(P0_SYNTH),
                "--out",
                str(frozen_out),
                "--confirm-freeze",
                "--json",
            ]
        )
        == 0
    )
    freeze_payload = json.loads(capsys.readouterr().out)
    assert freeze_payload["status"] == "frozen"

    # Second freeze onto same immutable file is rejected
    assert (
        cli_main(
            [
                "protocol",
                "freeze",
                str(P0_SYNTH),
                "--out",
                str(frozen_out),
                "--confirm-freeze",
            ]
        )
        == 2
    )
    capsys.readouterr()

    ds_dir = tmp_path / "ds"
    ingest_synthetic_fixture(SYNTH_RAW, ds_dir)
    assert (
        cli_main(
            [
                "run",
                "plan",
                "--protocol",
                str(frozen_out),
                "--dataset-dir",
                str(ds_dir),
                "--replicates",
                "2",
                "--json",
            ]
        )
        == 0
    )
    plan_payload = json.loads(capsys.readouterr().out)
    assert plan_payload["total_runs"] == 4
    assert plan_payload["is_synthetic_fixture"] is True


@pytest.mark.integration
def test_cli_run_start_status_and_real_subprocess_cancellation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ds_dir = tmp_path / "ds"
    ingest_synthetic_fixture(SYNTH_RAW, ds_dir)

    # Normal foreground start + status
    work_ok = tmp_path / "work_ok"
    assert (
        cli_main(
            [
                "run",
                "start",
                "--protocol",
                str(P0_SYNTH),
                "--dataset-dir",
                str(ds_dir),
                "--work-dir",
                str(work_ok),
                "--replicates",
                "1",
                "--json",
            ]
        )
        == 0
    )
    start_ok = json.loads(capsys.readouterr().out)
    assert start_ok["status"] == "succeeded"
    assert len(start_ok["run_dirs"]) == 2

    assert cli_main(["run", "status", "--work-dir", str(work_ok), "--json"]) == 0
    status_ok = json.loads(capsys.readouterr().out)
    assert status_ok["status"] == "succeeded"
    assert len(status_ok["runs"]) == 2

    # Multi-replicate detached run so cancel happens while subprocess is genuinely executing
    slow_proto = tmp_path / "slow_synth.yaml"
    proto_doc = yaml.safe_load(P0_SYNTH.read_text(encoding="utf-8"))
    proto_doc["seeds"]["replicates"] = 25
    slow_proto.write_text(yaml.safe_dump(proto_doc, sort_keys=False), encoding="utf-8")

    work_cancel = tmp_path / "work_cancel"
    assert (
        cli_main(
            [
                "run",
                "start",
                "--protocol",
                str(slow_proto),
                "--dataset-dir",
                str(ds_dir),
                "--work-dir",
                str(work_cancel),
                "--detach",
                "--json",
            ]
        )
        == 0
    )
    detached_info = json.loads(capsys.readouterr().out)
    assert detached_info["pid"] is not None

    # Wait briefly for child subprocess to advance into running state before cancelling
    state_file = work_cancel / "job_state.json"
    for _ in range(40):
        cur_state = json.loads(state_file.read_text(encoding="utf-8"))
        if cur_state.get("status") == "running":
            break
        time.sleep(0.1)

    assert cli_main(["run", "cancel", "--work-dir", str(work_cancel), "--json"]) == 0
    cancel_payload = json.loads(capsys.readouterr().out)
    assert cancel_payload["status"] == "cancelled"

    time.sleep(0.2)
    assert cli_main(["run", "status", "--work-dir", str(work_cancel), "--json"]) == 0
    post_status = json.loads(capsys.readouterr().out)
    assert post_status["status"] == "cancelled"
    assert post_status["process_alive"] is False
