"""Unit tests for Phase 6 publication archival, bundle SHA-256 verification, and citation audit."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from synapse_analysis import run_paired_analysis
from synapse_data import ingest_synthetic_fixture
from synapse_experiments import run_protocol_experiment
from synapse_publication import (
    audit_citation_register,
    build_publication_release_archive,
    export_evidence_bundle,
    generate_evidence_linked_methods,
    verify_evidence_bundle,
    verify_publication_release_archive,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_audit_citation_register_passes_repo_and_flags_preprints(tmp_path: Path) -> None:
    report = audit_citation_register(REPO_ROOT / "research" / "literature" / "source_register.yaml")
    assert report["valid"] is True
    assert report["total_references"] >= 35
    assert "jones2025_biorxiv" in report["preprint_ref_ids"]

    bad_reg = tmp_path / "bad_register.yaml"
    bad_reg.write_text(
        """
sources:
  - id: group1
    references:
      - ref_id: dup1
        citation_short: "A (2024)"
        doi: "10.1000/a"
        claim_scope: "test"
      - ref_id: dup1
        citation_short: "B (2024)"
        doi: "10.1000/b"
        claim_scope: "test"
""",
        encoding="utf-8",
    )
    bad_report = audit_citation_register(bad_reg)
    assert bad_report["valid"] is False
    assert any("Duplicate ref_id" in err for err in bad_report["errors"])


@pytest.mark.unit
def test_bundle_verification_and_release_archive_fail_closed_on_tampering(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    runs_dir = tmp_path / "runs"
    analysis_dir = tmp_path / "analysis"
    bundle_dir = tmp_path / "bundle_synth"

    ingest_synthetic_fixture(
        REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1", dataset_dir
    )
    run_protocol_experiment(
        protocol_path=REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml",
        dataset_dir=dataset_dir,
        runs_dir=runs_dir,
        replicates_override=2,
        repo_root=REPO_ROOT,
    )
    run_paired_analysis(
        runs_dir=runs_dir,
        out_dir=analysis_dir,
        baseline_condition="baseline",
        treatment_condition="inhibitory_silencing",
        target_neuron_id="9007199254740996",
    )
    export_evidence_bundle(analysis_dir=analysis_dir, out_dir=bundle_dir)

    bundle_ok = verify_evidence_bundle(bundle_dir)
    assert bundle_ok["valid"] is True
    assert bundle_ok["checked_files"] == 5
    assert bundle_ok["failed_run_count"] == 0

    methods_out = tmp_path / "methods.md"
    m_res = generate_evidence_linked_methods(
        repo_root=REPO_ROOT,
        protocol_path=REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml",
        analysis_dirs=[analysis_dir],
        out_path=methods_out,
    )
    assert m_res["n_analyses"] == 1
    assert "[HUMAN AUTHOR INPUT REQUIRED]" in methods_out.read_text(encoding="utf-8")

    archive_dir = tmp_path / "release_archive"
    manifest_path = build_publication_release_archive(
        repo_root=REPO_ROOT,
        out_dir=archive_dir,
        include_bundle_dirs=[bundle_dir],
        release_version="0.1.0.test",
    )
    assert manifest_path.is_file()
    archive_ok = verify_publication_release_archive(archive_dir)
    assert archive_ok["valid"] is True
    assert archive_ok["zip_members"] > 10

    zip_path = archive_dir / "synapse_release_0.1.0.test.zip"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert not any(n.startswith("data/") or n.endswith("spikes.parquet") for n in names)

    # Tamper a file inside the bundle and ensure verify_evidence_bundle fails closed
    csv_path = bundle_dir / "tables" / "figure1_source_data.csv"
    csv_path.write_text("tampered\n", encoding="utf-8")
    bundle_tampered = verify_evidence_bundle(bundle_dir)
    assert bundle_tampered["valid"] is False
    assert any("SHA-256 mismatch" in err for err in bundle_tampered["errors"])

    # Path traversal inside bundle_manifest.json must fail closed
    manifest_file = bundle_dir / "provenance" / "bundle_manifest.json"
    mdata = json.loads(manifest_file.read_text(encoding="utf-8"))
    mdata["files"][0]["path"] = "../../etc/passwd"
    manifest_file.write_text(json.dumps(mdata), encoding="utf-8")
    bundle_trav = verify_evidence_bundle(bundle_dir)
    assert bundle_trav["valid"] is False
    assert any("Path traversal" in err for err in bundle_trav["errors"])
