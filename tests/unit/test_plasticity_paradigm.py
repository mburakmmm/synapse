"""Unit tests for L2 mushroom-body dopamine plasticity and conditioning paradigm gates."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from synapse_core import (
    MBPlasticityParameters,
    compute_preference_metrics,
    run_conditioning_paradigm,
    verify_plasticity_paradigm_gates,
)


@pytest.mark.unit
def test_plasticity_parameter_validation_and_canonical_hash() -> None:
    p1 = MBPlasticityParameters()
    p2 = MBPlasticityParameters()
    assert p1.canonical_sha256() == p2.canonical_sha256()
    assert p1.model_level == "L2"
    assert p1.solver == "rk4"

    naive_metrics = compute_preference_metrics(1.0, 1.0, 1.0, 1.0, p1)
    assert naive_metrics["preference_index_proxy"] == pytest.approx(0.0)

    with pytest.raises(ValidationError):
        MBPlasticityParameters(tau_e_s=0.0)
    with pytest.raises(ValidationError):
        MBPlasticityParameters(w_min=1.0, w_init=0.8)
    with pytest.raises(ValidationError):
        MBPlasticityParameters(eta_ltd_pam=-0.1)
    with pytest.raises(ValidationError):
        MBPlasticityParameters(omission_gain=float("nan"))


@pytest.mark.unit
def test_plasticity_gates_pass_and_negative_failures_block_paradigm() -> None:
    params = MBPlasticityParameters()
    gate = verify_plasticity_paradigm_gates(params)
    assert gate["overall_passed"] is True
    for g in gate["gates"].values():
        assert g["passed"] is True

    assert gate["gates"]["acquisition_specificity"]["w_avoid_cs_minus_abs_err"] < 1e-6
    assert gate["gates"]["parallel_memory_extinction"]["w_avoid_cs_plus_ext"] <= 0.65
    assert abs(gate["gates"]["negative_controls_null"]["yoked_unpaired_acq_pi"]) < 0.05
    assert gate["gates"]["negative_controls_null"]["sham_max_weight_dev"] == 0.0
    assert gate["gates"]["negative_controls_null"]["dan_blocked_max_abs_pi"] < 1e-9

    # Fail-closed gate checks: disabling PAM LTD or destroying temporal eligibility specificity
    no_ltd = MBPlasticityParameters(eta_ltd_pam=0.0)
    bad_gate_1 = verify_plasticity_paradigm_gates(no_ltd)
    assert bad_gate_1["overall_passed"] is False
    assert bad_gate_1["gates"]["acquisition_specificity"]["passed"] is False
    with pytest.raises(RuntimeError, match="Refusing to run conditioning paradigm"):
        run_conditioning_paradigm(no_ltd, require_verified_gate=True)

    slow_trace = MBPlasticityParameters(tau_e_s=1000.0)
    bad_gate_2 = verify_plasticity_paradigm_gates(slow_trace)
    assert bad_gate_2["overall_passed"] is False
    with pytest.raises(RuntimeError, match="Refusing to run conditioning paradigm"):
        run_conditioning_paradigm(slow_trace, require_verified_gate=True)


@pytest.mark.unit
def test_conditioning_paradigm_arms_and_l2_to_l1_snapshots() -> None:
    summary, trajectories = run_conditioning_paradigm(
        MBPlasticityParameters(),
        require_verified_gate=True,
    )
    assert summary["gate_overall_passed"] is True
    arms = summary["arms"]
    assert set(arms) == {
        "paired_conditioning",
        "spontaneous_recovery_only",
        "yoked_unpaired",
        "sham_no_stimulus",
        "dan_blocked",
    }
    paired_snaps = arms["paired_conditioning"]["phase_snapshots"]
    spont_snaps = arms["spontaneous_recovery_only"]["phase_snapshots"]
    assert paired_snaps["reinstatement"]["pi_proxy"] > spont_snaps["reinstatement"]["pi_proxy"]
    assert arms["sham_no_stimulus"]["max_abs_pi_proxy"] == 0.0
    assert arms["dan_blocked"]["max_abs_pi_proxy"] == 0.0
    assert len(summary["l2_to_l1_weight_snapshots"]) == 5
    assert "paired_conditioning" in trajectories
