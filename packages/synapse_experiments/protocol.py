"""Versioned protocol loading, JSON Schema checks, and fail-closed executability gates."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class ProtocolValidationError(ValueError):
    """Raised when an experiment protocol violates schema or executability rules."""


def default_protocol_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "protocol_revision.v1.schema.json"


def default_run_manifest_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "run_manifest.v1.schema.json"


def _find_unresolved_paths(node: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            hits.extend(_find_unresolved_paths(value, path))
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            path = f"{prefix}[{idx}]"
            hits.extend(_find_unresolved_paths(item, path))
    elif isinstance(node, str) and node.strip().upper() == "UNRESOLVED":
        hits.append(prefix or "<root>")
    return hits


def validate_run_manifest_schema(
    manifest: dict[str, Any],
    schema_path: Path | None = None,
) -> None:
    """Validate a run manifest against ``schemas/run_manifest.v1.schema.json``."""
    resolved = default_run_manifest_schema_path() if schema_path is None else schema_path
    schema = json.loads(resolved.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        raise ProtocolValidationError(f"Run manifest schema violation: {first.message}")


def load_and_validate_protocol(
    path: Path,
    *,
    schema_path: Path | None = None,
    require_executable: bool = True,
) -> tuple[dict[str, Any], str]:
    """Load YAML protocol, validate schema and constraints, and return ``(dict, sha256)``."""
    if not path.is_file():
        raise ProtocolValidationError(f"Protocol file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProtocolValidationError("Protocol YAML root must be a mapping")

    resolved_schema = default_protocol_schema_path() if schema_path is None else schema_path
    schema = json.loads(resolved_schema.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(raw), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        raise ProtocolValidationError(f"Protocol schema violation: {first.message}")

    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    protocol_sha256 = hashlib.sha256(canonical).hexdigest()

    if not require_executable:
        return raw, protocol_sha256

    unresolved = _find_unresolved_paths(raw)
    if unresolved:
        raise ProtocolValidationError(
            f"Protocol contains UNRESOLVED placeholders at: {', '.join(unresolved)}"
        )

    if raw["analysis_intent"] == "confirmatory" and raw["status"] not in ("approved", "frozen"):
        raise ProtocolValidationError(
            "Confirmatory protocol requires status='approved' or 'frozen' before execution"
        )

    backend = raw["model"]["backend"]
    if backend != "brian2_cpu":
        raise ProtocolValidationError(
            f"Unsupported backend {backend!r} in Phase 0; expected 'brian2_cpu'"
        )

    stim = raw["stimulus_schedule"]
    if not isinstance(stim, dict) or not isinstance(stim.get("duration_s"), (int, float)):
        raise ProtocolValidationError("stimulus_schedule.duration_s must be numeric")
    duration_s = float(stim["duration_s"])
    if duration_s <= 0.0:
        raise ProtocolValidationError("stimulus_schedule.duration_s must be > 0")

    mw = raw["measurement_window"]
    if (
        not isinstance(mw, dict)
        or not isinstance(mw.get("start_s"), (int, float))
        or not isinstance(mw.get("end_s"), (int, float))
    ):
        raise ProtocolValidationError("measurement_window must specify numeric start_s and end_s")
    m_start = float(mw["start_s"])
    m_end = float(mw["end_s"])
    if m_start < 0.0 or m_end <= m_start or m_end > duration_s:
        raise ProtocolValidationError(
            f"Invalid measurement_window [{m_start}, {m_end}] for duration_s={duration_s}"
        )

    seeds = raw["seeds"]
    if (
        isinstance(seeds["master"], bool)
        or not isinstance(seeds["master"], int)
        or seeds["master"] < 0
    ):
        raise ProtocolValidationError("seeds.master must be a non-negative integer")
    if (
        isinstance(seeds["replicates"], bool)
        or not isinstance(seeds["replicates"], int)
        or seeds["replicates"] < 1
    ):
        raise ProtocolValidationError("seeds.replicates must be an integer >= 1")

    res = raw["resources"]
    if (
        not isinstance(res.get("max_wall_seconds"), (int, float))
        or float(res["max_wall_seconds"]) <= 0
    ):
        raise ProtocolValidationError("resources.max_wall_seconds must be > 0")
    if (
        isinstance(res.get("max_output_bytes"), bool)
        or not isinstance(res.get("max_output_bytes"), int)
        or int(res["max_output_bytes"]) <= 0
    ):
        raise ProtocolValidationError("resources.max_output_bytes must be a positive integer")

    seen_conds: set[str] = set()
    for cond in raw["conditions"]:
        cid = cond["id"]
        if cid in seen_conds:
            raise ProtocolValidationError(f"Duplicate condition id {cid!r}")
        seen_conds.add(cid)
        for idx, iv in enumerate(cond["interventions"]):
            if not isinstance(iv, dict) or "kind" not in iv:
                raise ProtocolValidationError(
                    f"Condition {cid!r} intervention[{idx}] must be a dict with 'kind'"
                )
            if iv["kind"] != "sham":
                targets = iv.get("target_neuron_ids")
                if not isinstance(targets, list) or len(targets) == 0:
                    raise ProtocolValidationError(
                        f"Non-sham intervention[{idx}] in condition {cid!r} requires non-empty "
                        "target_neuron_ids"
                    )

    return raw, protocol_sha256


def freeze_protocol(
    protocol_path: Path,
    out_path: Path | None = None,
    *,
    confirmed: bool = False,
    schema_path: Path | None = None,
) -> tuple[Path, dict[str, Any], str]:
    """Freeze a validated protocol into an immutable YAML revision after human confirmation."""
    if not confirmed:
        raise ProtocolValidationError(
            "Protocol freeze requires explicit confirmation (confirmed=True); "
            "refusing automatic freeze"
        )

    raw, _ = load_and_validate_protocol(
        protocol_path,
        schema_path=schema_path,
        require_executable=True,
    )

    target_path = (
        protocol_path.with_name(f"{protocol_path.stem}.frozen.yaml")
        if out_path is None
        else out_path
    )
    if target_path.exists():
        raise ProtocolValidationError(
            f"Refusing to overwrite existing protocol artifact at {target_path}; "
            "frozen revisions must remain immutable"
        )

    frozen_doc: dict[str, Any] = json.loads(json.dumps(raw))
    frozen_doc["status"] = "frozen"
    frozen_doc["frozen_at_utc"] = datetime.now(UTC).isoformat()

    target_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(frozen_doc, sort_keys=False)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target_path.parent),
        prefix=f".{target_path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        os.replace(tmp_path, target_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    validated, frozen_sha = load_and_validate_protocol(
        target_path,
        schema_path=schema_path,
        require_executable=True,
    )
    return target_path, validated, frozen_sha
