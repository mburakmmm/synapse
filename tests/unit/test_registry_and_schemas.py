"""Unit tests for JSON Schema validity and approval-gated SourceRegistry."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from synapse_data import ApprovalRequiredError, build_default_registry

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema_name",
    [
        "dataset_manifest.v1.schema.json",
        "protocol_revision.v1.schema.json",
        "run_manifest.v1.schema.json",
    ],
)
def test_json_schemas_are_valid_draft_2020_12(schema_name: str) -> None:
    schema_path = REPO_ROOT / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.unit
def test_source_registry_plans_and_approval_gates(tmp_path: Path) -> None:
    reg = build_default_registry()
    ids = reg.list_dataset_ids()
    assert set(ids) == {
        "synthetic_microcircuit_v1",
        "flywire_fafb_v630",
        "flywire_fafb_v783",
        "malecns_v1_0",
    }

    synth_plan = reg.get("synthetic_microcircuit_v1").plan()
    assert synth_plan.is_synthetic_fixture is True
    assert synth_plan.approval_required is False

    v630_plan = reg.get("flywire_fafb_v630").plan()
    assert v630_plan.is_synthetic_fixture is False
    assert v630_plan.approval_required is True
    assert v630_plan.total_estimated_bytes == 3057611 + 86630944

    malecns_plan = reg.get("malecns_v1_0").plan()
    assert malecns_plan.is_synthetic_fixture is False
    assert malecns_plan.approval_required is True
    assert malecns_plan.total_estimated_bytes == 14483314 + 43282834 + 1051241946

    for bio_id in ("flywire_fafb_v630", "flywire_fafb_v783", "malecns_v1_0"):
        with pytest.raises(ApprovalRequiredError, match="explicit user authorization"):
            reg.get(bio_id).fetch(tmp_path, approved=False)
