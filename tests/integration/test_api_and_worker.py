"""Integration tests for Alembic, FastAPI /api/v1, durable worker, cancel, retry, and backup."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from synapse_api.app import create_app
from synapse_api.config import Settings
from synapse_api.db import create_db_engine, run_migrations_downgrade, run_migrations_upgrade
from synapse_data import ingest_synthetic_fixture
from synapse_worker.executor import WorkerRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTH_RAW = REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1"
P0_SYNTH = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"


def _make_settings(tmp_path: Path) -> Settings:
    data_root = tmp_path / "data"
    runs_root = tmp_path / "runs"
    protocols_root = tmp_path / "protocols"
    data_root.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)
    protocols_root.mkdir(parents=True, exist_ok=True)
    db_file = runs_root / "test_lab.sqlite3"
    return Settings(
        repo_root=REPO_ROOT,
        database_url=f"sqlite:///{db_file.as_posix()}",
        data_root=data_root,
        runs_root=runs_root,
        protocols_root=protocols_root,
    )


@pytest.mark.integration
def test_alembic_upgrade_downgrade_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "migrations_test.sqlite3"
    db_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_upgrade(db_url, "head")
    eng = create_db_engine(db_url)
    try:
        tables_up = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    assert {"protocol_revisions", "experiments", "jobs", "audit_events"} <= tables_up

    run_migrations_downgrade(db_url, "base")
    eng_down = create_db_engine(db_url)
    try:
        tables_down = set(inspect(eng_down).get_table_names())
    finally:
        eng_down.dispose()
    assert not ({"protocol_revisions", "experiments", "jobs", "audit_events"} & tables_down)

    run_migrations_upgrade(db_url, "head")
    eng_reup = create_db_engine(db_url)
    try:
        tables_reup = set(inspect(eng_reup).get_table_names())
    finally:
        eng_reup.dispose()
    assert {"protocol_revisions", "experiments", "jobs", "audit_events"} <= tables_reup


@pytest.mark.integration
def test_api_and_worker_full_fixture_lifecycle_security_cancel_and_backup(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    ingest_synthetic_fixture(
        SYNTH_RAW, settings.data_root / "curated" / "synthetic_microcircuit_v1"
    )
    shutil.copy2(P0_SYNTH, settings.protocols_root / "P0-SYNTH-001.yaml")

    app = create_app(settings)
    with TestClient(app) as client:
        # 1. Health, datasets, 64-bit string IDs, bounded subgraph
        h = client.get("/api/v1/health")
        assert h.status_code == 200
        assert "RUO" in h.json()["ruo_notice"]
        storage = h.json()["storage"]
        assert isinstance(storage["data_dir_exists"], bool)
        assert isinstance(storage["runs_dir_exists"], bool)

        neurons_res = client.get("/api/v1/datasets/synthetic_microcircuit_v1/neurons")
        assert neurons_res.status_code == 200
        neuron_ids = [n["source_neuron_id"] for n in neurons_res.json()["neurons"]]
        assert "9007199254740996" in neuron_ids

        sub_res = client.post(
            "/api/v1/datasets/synthetic_microcircuit_v1/subgraph",
            json={
                "seed_neuron_ids": ["9007199254740993"],
                "hops": 1,
                "direction": "outgoing",
                "min_synapses": 1,
                "max_nodes": 10,
            },
        )
        assert sub_res.status_code == 200
        sub_body = sub_res.json()
        assert sub_body["metadata"]["n_selected_neurons"] >= 2
        assert all(isinstance(node["source_neuron_id"], str) for node in sub_body["nodes"])
        assert any(
            node["is_seed"] and "cell_type" in node and "neurotransmitter" in node
            for node in sub_body["nodes"]
        )

        # 2. Path traversal and unconfirmed freeze gates
        trav_proto = client.post(
            "/api/v1/protocols/validate",
            json={"protocol_path": "../outside.yaml"},
        )
        assert trav_proto.status_code == 403
        assert trav_proto.json()["error"]["code"] == "path_containment_violation"

        unconfirmed_freeze = client.post(
            "/api/v1/protocols/freeze",
            json={"protocol_path": "P0-SYNTH-001.yaml", "confirmed": False},
        )
        assert unconfirmed_freeze.status_code == 400

        frozen_res = client.post(
            "/api/v1/protocols/freeze",
            json={"protocol_path": "P0-SYNTH-001.yaml", "confirmed": True},
        )
        assert frozen_res.status_code == 200
        frozen_rel = frozen_res.json()["frozen_path"]

        # 3. Dry-run experiment plan & idempotent job submission
        plan_res = client.post(
            "/api/v1/experiments/plan",
            json={
                "protocol_path": frozen_rel,
                "dataset_id": "synthetic_microcircuit_v1",
                "replicates": 2,
            },
        )
        assert plan_res.status_code == 200
        assert plan_res.json()["total_runs"] == 4

        job_payload = {
            "kind": "protocol_experiment",
            "protocol_path": frozen_rel,
            "dataset_id": "synthetic_microcircuit_v1",
            "work_dir_name": "api_e2e_exp",
            "replicates": 2,
            "workers": 1,
        }
        j1 = client.post("/api/v1/jobs", json=job_payload, headers={"Idempotency-Key": "e2e-k1"})
        j2 = client.post("/api/v1/jobs", json=job_payload, headers={"Idempotency-Key": "e2e-k1"})
        assert j1.status_code == 201 and j1.json()["created"] is True
        assert j2.status_code == 200 and j2.json()["created"] is False
        sim_job_id = j1.json()["job"]["job_id"]

        # 4. Worker executes experiment subprocess
        worker = WorkerRunner(settings, worker_id="test-worker-1", migrate_on_start=False)
        try:
            assert worker.run_once(timeout_s=120.0) == sim_job_id
            sim_detail = client.get(f"/api/v1/jobs/{sim_job_id}").json()["job"]
            assert sim_detail["status"] == "succeeded"
            assert sim_detail["result"]["n_runs_completed"] == 4

            # Verify protocol YAML content endpoint & traversal rejection
            proto_yaml_res = client.get(
                "/api/v1/protocols/content",
                params={"protocol_path": frozen_rel},
            )
            assert proto_yaml_res.status_code == 200
            assert "protocol_id:" in proto_yaml_res.json()["yaml_text"]
            bad_proto_res = client.get(
                "/api/v1/protocols/content",
                params={"protocol_path": "../../AGENTS.md"},
            )
            assert bad_proto_res.status_code == 403

            # Verify /api/v1/models exposes L1 LIF, L2 plasticity, and L3 circadian models
            models_res = client.get("/api/v1/models")
            assert models_res.status_code == 200
            model_ids = {m["model_id"]: m for m in models_res.json()["models"]}
            assert "mb_dopamine_plasticity_v1" in model_ids
            assert model_ids["mb_dopamine_plasticity_v1"]["model_level"] == "L2"
            assert "leloup_goldbeter_1998_two_process_v1" in model_ids
            assert model_ids["leloup_goldbeter_1998_two_process_v1"]["model_level"] == "L3"

            # Verify /api/v1/studies module UI state taxonomy (§10)
            studies_res = client.get("/api/v1/studies")
            assert studies_res.status_code == 200
            studies_body = studies_res.json()
            assert "sleep" in studies_body
            assert "addiction" in studies_body
            allowed_states = {
                "planned",
                "experimental",
                "reproduced",
                "validated_for_declared_endpoint",
            }
            for mod in studies_body["modules"]:
                assert mod["ui_state"] in allowed_states

            # Verify run discovery, protocol_id filter, and artifact traversal rejection
            runs_res = client.get("/api/v1/runs").json()
            assert runs_res["total"] == 4
            filtered_runs = client.get(
                "/api/v1/runs",
                params={"protocol_id": runs_res["runs"][0]["protocol_id"]},
            ).json()
            assert filtered_runs["total"] == 4
            empty_filtered = client.get(
                "/api/v1/runs",
                params={"protocol_id": "NONEXISTENT-PROTOCOL"},
            ).json()
            assert empty_filtered["total"] == 0
            sample_run_id = runs_res["runs"][0]["run_id"]
            ok_art = client.get(f"/api/v1/runs/{sample_run_id}/artifacts/metrics.parquet")
            assert ok_art.status_code == 200
            bad_art = client.get(
                f"/api/v1/runs/{sample_run_id}/artifacts/%2e%2e%2f%2e%2e%2ftest_lab.sqlite3"
            )
            assert bad_art.status_code == 403

            # 5. Queue and execute analysis + export_bundle jobs
            an_job = client.post(
                "/api/v1/jobs",
                json={
                    "kind": "analysis",
                    "runs_rel_dir": "api_e2e_exp/runs",
                    "out_rel_dir": "api_e2e_exp/analysis",
                    "baseline_condition": "baseline",
                    "treatment_condition": "inhibitory_silencing",
                    "target_neuron_id": "9007199254740996",
                },
            ).json()["job"]["job_id"]
            assert worker.run_once(timeout_s=60.0) == an_job

            analyses = client.get("/api/v1/analyses").json()["analyses"]
            assert len(analyses) == 1
            assert analyses[0]["paired_metrics"]["permutation_test"]["n_pairs"] == 2

            ex_job = client.post(
                "/api/v1/jobs",
                json={
                    "kind": "export_bundle",
                    "analysis_rel_dir": "api_e2e_exp/analysis",
                    "out_rel_dir": "api_e2e_exp/bundle",
                },
            ).json()["job"]["job_id"]
            assert worker.run_once(timeout_s=60.0) == ex_job

            exports = client.get("/api/v1/exports").json()["exports"]
            assert len(exports) == 1
            ex_key = exports[0]["export_key"]
            svg_res = client.get(
                f"/api/v1/exports/{ex_key}/files/figures/firing_rate_comparison.svg"
            )
            assert svg_res.status_code == 200

            # 6. Cooperative cancellation of a real running worker subprocess + retry lineage
            slow_doc = yaml.safe_load(P0_SYNTH.read_text(encoding="utf-8"))
            slow_doc["seeds"]["replicates"] = 25
            slow_proto_path = settings.protocols_root / "P0-SYNTH-SLOW.yaml"
            slow_proto_path.write_text(yaml.safe_dump(slow_doc, sort_keys=False), encoding="utf-8")

            c_job_id = client.post(
                "/api/v1/jobs",
                json={
                    "kind": "protocol_experiment",
                    "protocol_path": "P0-SYNTH-SLOW.yaml",
                    "dataset_id": "synthetic_microcircuit_v1",
                    "work_dir_name": "api_cancel_exp",
                    "workers": 1,
                },
            ).json()["job"]["job_id"]

            worker_outcome: dict[str, Any] = {}

            def _run_worker() -> None:
                worker_outcome["handled"] = worker.run_once(timeout_s=120.0, poll_interval_s=0.05)

            th = threading.Thread(target=_run_worker, daemon=True)
            th.start()

            for _ in range(80):
                cur = client.get(f"/api/v1/jobs/{c_job_id}").json()["job"]
                if cur["status"] == "running" and cur["worker_pid"] is not None:
                    break
                time.sleep(0.1)

            cancel_res = client.post(f"/api/v1/jobs/{c_job_id}/cancel")
            assert cancel_res.status_code == 200
            th.join(timeout=15.0)
            assert not th.is_alive()

            after_cancel = client.get(f"/api/v1/jobs/{c_job_id}").json()["job"]
            assert after_cancel["status"] == "cancelled"

            retry_res = client.post(f"/api/v1/jobs/{c_job_id}/retry")
            assert retry_res.status_code == 201
            retry_job = retry_res.json()["job"]
            assert retry_job["parent_job_id"] == c_job_id
            assert retry_job["attempt_number"] == 2
            assert retry_job["status"] == "queued"

            # Verify audit events recorded across freeze, submit, cancel, and retry
            audit_rows = client.get("/api/v1/audit?limit=100").json()["events"]
            audit_actions = {ev["action"] for ev in audit_rows}
            expected_actions = {"protocol.frozen", "job.submitted", "job.cancelled", "job.retried"}
            assert expected_actions <= audit_actions
        finally:
            worker.close()

    # 7. Backup & restore verification script
    db_file = settings.runs_root / "test_lab.sqlite3"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "backup_restore_verify.py"),
            "--db-path",
            str(db_file),
            "--runs-dir",
            str(settings.runs_root / "api_e2e_exp"),
            "--work-dir",
            str(tmp_path / "backup_verify"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    backup_report = json.loads(proc.stdout)
    assert backup_report["verified"] is True
    assert backup_report["artifact_file_count"] > 0
