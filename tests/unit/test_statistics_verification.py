"""Known-answer unit tests for Phase 3 statistics, model validation, freeze, and dry-run plan."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.stats import false_discovery_control, permutation_test

from synapse_analysis import bh_fdr_adjust, local_sensitivity_summary, paired_permutation_test
from synapse_core import LIFParameters, validate_model_spec
from synapse_data import ingest_synthetic_fixture
from synapse_experiments import ProtocolValidationError, freeze_protocol, plan_protocol_experiment

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTH_RAW = REPO_ROOT / "tests" / "fixtures" / "synthetic_microcircuit_v1"
P0_SYNTH = REPO_ROOT / "research" / "protocols" / "P0-SYNTH-001.yaml"


@pytest.mark.unit
def test_paired_permutation_exact_sign_flip_and_monte_carlo() -> None:
    # Deterministic zero difference guard
    zero_res = paired_permutation_test([0.0, 0.0, 0.0, 0.0])
    assert zero_res["method"] == "deterministic_zero_difference"
    assert zero_res["two_sided_p_value"] == pytest.approx(1.0)
    assert zero_res["deterministic_zero_variance"] is True

    # Identical nonzero paired differences: only (+1)^4 and (-1)^4 achieve |mean|=2.0 -> 2/16
    const_res = paired_permutation_test([2.0, 2.0, 2.0, 2.0], exact_threshold=14)
    assert const_res["method"] == "exact_sign_flip"
    assert const_res["n_evaluations"] == 16
    assert const_res["two_sided_p_value"] == pytest.approx(2.0 / 16.0)

    # Cross-check against scipy.stats.permutation_test (paired mean difference)
    diffs = np.array([1.2, 3.4, -0.8, 4.1, 2.5], dtype=np.float64)
    ours = paired_permutation_test(diffs, exact_threshold=14)
    zeros = np.zeros_like(diffs)
    scipy_res = permutation_test(
        (diffs, zeros),
        lambda x, y, axis: np.mean(x - y, axis=axis),
        permutation_type="samples",
        alternative="two-sided",
        n_resamples=99999,
    )
    assert ours["method"] == "exact_sign_flip"
    assert ours["two_sided_p_value"] == pytest.approx(float(scipy_res.pvalue), abs=1e-12)

    # Monte Carlo determinism for n > exact_threshold
    big = np.linspace(1.0, 5.0, 20)
    mc1 = paired_permutation_test(big, seed=42, n_permutations=2000, exact_threshold=14)
    mc2 = paired_permutation_test(big, seed=42, n_permutations=2000, exact_threshold=14)
    assert mc1["method"] == "monte_carlo_sign_flip"
    assert mc1["two_sided_p_value"] == mc2["two_sided_p_value"]
    assert 0.0 < mc1["two_sided_p_value"] <= 1.0


@pytest.mark.unit
def test_bh_fdr_adjust_matches_scipy_and_rejects_invalid() -> None:
    assert bh_fdr_adjust([]) == []
    ps = [0.001, 0.008, 0.039, 0.041, 0.42, 0.78, 0.008]
    expected = false_discovery_control(ps, method="bh")
    observed = bh_fdr_adjust(ps)
    assert np.allclose(observed, expected, atol=1e-12)

    with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
        bh_fdr_adjust([0.1, 1.2])


@pytest.mark.unit
def test_local_sensitivity_summary() -> None:
    inc = local_sensitivity_summary(
        "w_syn_v",
        [0.00020, 0.000275, 0.00035],
        [40.0, 68.0, 92.0],
        baseline_value=0.000275,
    )
    assert inc["trend"] == "monotone_increasing"
    assert inc["endpoint_range"] == pytest.approx(52.0)
    assert inc["max_abs_shift_from_baseline"] == pytest.approx(28.0)

    non_mono = local_sensitivity_summary(
        "tau_m_s",
        [0.01, 0.02, 0.03],
        [10.0, 25.0, 18.0],
        baseline_value=0.02,
    )
    assert non_mono["trend"] == "non_monotone"


@pytest.mark.unit
def test_validate_model_spec_freeze_gate_and_dry_run_plan(tmp_path: Path) -> None:
    ref = LIFParameters.shiu2024_reference()
    ref_params = ref.model_dump(mode="json")
    spec_ok: dict[str, object] = {
        "id": ref.model_id,
        "revision": ref.model_revision,
        "backend": "brian2_cpu",
        "parameter_manifest_sha256": ref.canonical_sha256(),
        "parameters": ref_params,
    }
    res = validate_model_spec(spec_ok)
    assert res["valid"] is True
    assert res["supported_on_cpu_reference"] is True
    assert res["gpu_verified"] is False
    assert res["parameter_manifest_sha256"] == ref.canonical_sha256()

    with pytest.raises(ValueError, match="brian2_cpu"):
        validate_model_spec({**spec_ok, "backend": "brian2_cuda"})

    with pytest.raises(ValueError, match="Unknown LIF model parameter"):
        validate_model_spec({**spec_ok, "parameters": {**ref_params, "tau_m": 0.02}})

    with pytest.raises(ProtocolValidationError, match="confirmed=True"):
        freeze_protocol(P0_SYNTH, out_path=tmp_path / "p0.frozen.yaml", confirmed=False)

    frozen_path, doc, sha = freeze_protocol(
        P0_SYNTH, out_path=tmp_path / "p0.frozen.yaml", confirmed=True
    )
    assert doc["status"] == "frozen"
    assert len(sha) == 64
    with pytest.raises(ProtocolValidationError, match="Refusing to overwrite"):
        freeze_protocol(P0_SYNTH, out_path=frozen_path, confirmed=True)

    ds_dir = tmp_path / "synth_ds"
    ingest_synthetic_fixture(SYNTH_RAW, ds_dir)
    plan = plan_protocol_experiment(frozen_path, ds_dir, replicates_override=2)
    assert plan["status"] == "planned"
    assert plan["is_synthetic_fixture"] is True
    assert plan["total_runs"] == 4
    assert plan["resource_estimate_per_run"]["n_neurons"] == 4
