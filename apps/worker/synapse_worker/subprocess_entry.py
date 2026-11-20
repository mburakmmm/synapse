"""Isolated allowlisted subprocess entrypoint executed by SYNAPSE worker."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from synapse_analysis import run_paired_analysis
from synapse_experiments import run_protocol_experiment
from synapse_publication import export_evidence_bundle


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def execute_allowlisted_job(spec_path: Path) -> Path:
    """Execute one allowlisted job spec in a clean subprocess without arbitrary code eval."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    kind = str(spec["kind"])
    payload = dict(spec["payload"])
    result_path = Path(spec["result_file"])

    result: dict[str, Any]
    if kind == "protocol_experiment":
        run_dirs = run_protocol_experiment(
            protocol_path=Path(payload["protocol_path"]),
            dataset_dir=Path(payload["dataset_dir"]),
            runs_dir=Path(payload["runs_dir"]),
            replicates_override=payload.get("replicates"),
            workers=int(payload.get("workers", 1)),
        )
        result = {
            "kind": kind,
            "n_runs_completed": len(run_dirs),
            "run_dirs": [str(p) for p in run_dirs],
        }
    elif kind == "analysis":
        manifest_path = run_paired_analysis(
            runs_dir=Path(payload["runs_dir"]),
            out_dir=Path(payload["out_dir"]),
            baseline_condition=str(payload["baseline_condition"]),
            treatment_condition=str(payload["treatment_condition"]),
            target_neuron_id=str(payload["target_neuron_id"]),
        )
        analysis_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = {
            "kind": kind,
            "analysis_manifest": str(manifest_path),
            "failed_run_count": analysis_data["failed_run_count"],
            "paired_metrics": analysis_data["paired_metrics"],
        }
    elif kind == "export_bundle":
        bundle_manifest = export_evidence_bundle(
            analysis_dir=Path(payload["analysis_dir"]),
            out_dir=Path(payload["out_dir"]),
        )
        result = {
            "kind": kind,
            "bundle_manifest": str(bundle_manifest),
        }
    else:
        raise ValueError(f"Rejected non-allowlisted worker job kind: {kind!r}")

    _write_json_atomic(result_path, result)
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser(description="SYNAPSE isolated job subprocess runner")
    parser.add_argument("--job-file", required=True)
    args = parser.parse_args()
    execute_allowlisted_job(Path(args.job_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
