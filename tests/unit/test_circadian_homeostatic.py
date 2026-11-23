"""Unit tests for L3 Leloup-Goldbeter circadian clock + two-process homeostat gates."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from synapse_core import (
    CircadianHomeostaticParameters,
    run_shift_work_experiment,
    verify_circadian_homeostatic_gates,
    wrap_phase_hours,
)


@pytest.mark.unit
def test_circadian_parameter_validation_and_canonical_hash() -> None:
    p1 = CircadianHomeostaticParameters()
    p2 = CircadianHomeostaticParameters()
    assert p1.canonical_sha256() == p2.canonical_sha256()
    assert p1.model_level == "L3"
    assert p1.tau_i_h == 8.76
    assert p1.tau_d_h == 9.51

    with pytest.raises(ValidationError):
        CircadianHomeostaticParameters(tau_i_h=0.0)
    with pytest.raises(ValidationError):
        CircadianHomeostaticParameters(l_mean=0.7, u_mean=0.5)
    with pytest.raises(ValidationError):
        CircadianHomeostaticParameters(s_min=1.0, s_max=0.5)
    with pytest.raises(ValidationError):
        CircadianHomeostaticParameters(v_sP=float("nan"))


@pytest.mark.unit
def test_wrap_phase_hours_bounds() -> None:
    assert wrap_phase_hours(21.6, 24.13) == pytest.approx(21.6 - 24.13)
    assert wrap_phase_hours(-21.6, 24.13) == pytest.approx(24.13 - 21.6)
    with pytest.raises(ValueError):
        wrap_phase_hours(1.0, 0.0)


@pytest.mark.unit
def test_circadian_gates_pass_and_negative_light_gate_blocks_shift_work() -> None:
    params = CircadianHomeostaticParameters()
    gate = verify_circadian_homeostatic_gates(params)
    assert gate["overall_passed"] is True
    assert gate["gates"]["dd_free_running_and_convergence"]["passed"] is True
    assert gate["gates"]["ld12_12_entrainment"]["passed"] is True
    assert gate["gates"]["light_pulse_prc"]["passed"] is True
    assert gate["gates"]["homeostatic_deprivation_rebound"]["passed"] is True

    # Negative control: disabling light TIM degradation fails PRC & blocks shift-work
    blind_params = CircadianHomeostaticParameters(v_dT_light=2.0)
    bad_gate = verify_circadian_homeostatic_gates(blind_params)
    assert bad_gate["overall_passed"] is False
    assert bad_gate["gates"]["light_pulse_prc"]["passed"] is False
    with pytest.raises(RuntimeError, match="Refusing to simulate shift-work"):
        run_shift_work_experiment(blind_params, require_verified_gate=True)


@pytest.mark.unit
def test_shift_work_schedules_and_phase_metrics() -> None:
    summary, trajectories = run_shift_work_experiment(
        CircadianHomeostaticParameters(),
        require_verified_gate=True,
    )
    assert summary["gate_overall_passed"] is True
    arms = summary["arms"]
    assert set(arms) == {
        "ld12_12_control",
        "deprivation_12h_recovery",
        "shift_delay_8h",
        "shift_advance_6h",
        "rotating_shift_8h",
    }
    assert arms["ld12_12_control"]["max_abs_phase_error_h"] < 0.25
    assert (
        arms["deprivation_12h_recovery"]["s_peak_overall"]
        > arms["ld12_12_control"]["s_peak_overall"] + 0.10
    )
    assert arms["shift_delay_8h"]["max_abs_phase_error_h"] > 3.0
    assert arms["shift_advance_6h"]["max_abs_phase_error_h"] > 3.0
    assert arms["shift_delay_8h"]["days_to_reentrain"] is not None
    assert arms["shift_advance_6h"]["days_to_reentrain"] is not None
    assert arms["rotating_shift_8h"]["days_to_reentrain"] is None
    assert len(summary["l3_to_l1_coupling_snapshots"]) == 3
    assert "shift_delay_8h" in trajectories
