"""Unit tests for hierarchical seed derivation and experiment protocol gating."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from synapse_core import derive_seed
from synapse_experiments import ProtocolValidationError, load_and_validate_protocol

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_derive_seed_determinism_and_sensitivity() -> None:
    s1 = derive_seed(42, experiment_id="P0", condition_id="baseline", replicate_id=0)
    s2 = derive_seed(42, experiment_id="P0", condition_id="baseline", replicate_id=0)
    assert s1 == s2
    assert 0 <= s1 <= 0x7FFFFFFF

    assert s1 != derive_seed(43, experiment_id="P0", condition_id="baseline", replicate_id=0)
    assert s1 != derive_seed(42, experiment_id="P1", condition_id="baseline", replicate_id=0)
    assert s1 != derive_seed(42, experiment_id="P0", condition_id="treated", replicate_id=0)
    assert s1 != derive_seed(42, experiment_id="P0", condition_id="baseline", replicate_id=1)
    assert s1 != derive_seed(
        42, experiment_id="P0", condition_id="baseline", replicate_id=0, stream="x"
    )


@pytest.mark.unit
def test_draft_protocol_rejected_when_unresolved_and_passes_p0_synth() -> None:
    draft_path = REPO_ROOT / "research" / "protocols" / "P1-BENCH-SHIU2024-draft.yaml"
    with pytest.raises(ProtocolValidationError, match="UNRESOLVED"):
        load_and_validate_protocol(draft_path, require_executable=True)

    # Structural check without executability gate succeeds on draft template
    draft_doc, _ = load_and_validate_protocol(draft_path, require_executable=False)
    assert draft_doc["status"] == "draft"

    p0_path = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"
    p0_doc, sha1 = load_and_validate_protocol(p0_path, require_executable=True)
    _, sha2 = load_and_validate_protocol(p0_path, require_executable=True)
    assert sha1 == sha2
    assert p0_doc["protocol_id"] == "P0-SYNTH-001"


@pytest.mark.unit
def test_confirmatory_protocol_requires_approved_or_frozen_and_nonempty_targets(
    tmp_path: Path,
) -> None:
    p0_raw = yaml.safe_load(
        (REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml").read_text(encoding="utf-8")
    )

    # Unapproved confirmatory protocol must fail closed
    unapproved = dict(p0_raw)
    unapproved["status"] = "draft"
    unapproved["analysis_intent"] = "confirmatory"
    unapproved_path = tmp_path / "unapproved.yaml"
    unapproved_path.write_text(yaml.safe_dump(unapproved), encoding="utf-8")
    with pytest.raises(ProtocolValidationError, match="Confirmatory protocol"):
        load_and_validate_protocol(unapproved_path, require_executable=True)

    # Empty non-sham intervention target set must fail closed
    empty_targets = dict(p0_raw)
    empty_targets["conditions"] = [
        {"id": "bad", "interventions": [{"kind": "neuron_silencing", "target_neuron_ids": []}]}
    ]
    empty_path = tmp_path / "empty_targets.yaml"
    empty_path.write_text(yaml.safe_dump(empty_targets), encoding="utf-8")
    with pytest.raises(ProtocolValidationError, match="non-empty target_neuron_ids"):
        load_and_validate_protocol(empty_path, require_executable=True)
