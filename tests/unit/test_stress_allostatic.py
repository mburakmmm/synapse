"""Unit tests for Phase 5C-3 L3 reactive-scope stress & allostatic ODEs (RUO)."""

from __future__ import annotations

import numpy as np
import pytest

from synapse_core import (
    STRESS_ARM_IDS,
    StressAllostaticParameters,
    run_stress_allostatic_panel,
    simulate_stress_schedule,
    stressor_intensity,
    verify_stress_allostatic_gates,
)


@pytest.mark.unit
def test_stress_allostatic_gates_pass_all_five_invariants() -> None:
    params = StressAllostaticParameters()
    report = verify_stress_allostatic_gates(params)
    assert report["overall_passed"] is True
    assert report["model_level"] == "L3"
    assert report["solver"] == "RK45"
    assert len(report["gates"]) == 5
    for gate in report["gates"].values():
        assert gate["passed"] is True

    g1 = report["gates"]["rk45_convergence_and_bounds"]
    assert g1["max_abs_diff"] < 1e-4
    g4 = report["gates"]["chronic_allostatic_overload_separation"]
    assert g4["chronic_vs_acute_load_ratio"] > 3.0
    assert g4["late_bout_a_peak"] > g4["first_bout_a_peak"]


@pytest.mark.unit
def test_stress_ruo_guard_bounds_and_trajectory_shapes() -> None:
    with pytest.raises(ValueError, match="diagnostic_label_guard_enabled"):
        StressAllostaticParameters(diagnostic_label_guard_enabled=False)

    with pytest.raises(ValueError):
        StressAllostaticParameters(tau_a_h=0.0)

    params = StressAllostaticParameters()
    assert stressor_intensity("sham_zero_stressor", 10.0, params) == 0.0
    assert stressor_intensity("acute_single_threat", 4.25, params) == 1.0

    with pytest.raises(ValueError, match="arm_id"):
        simulate_stress_schedule("nonexistent_arm", params)

    sham = simulate_stress_schedule("sham_zero_stressor", params)
    assert np.allclose(sham.arousal_a, 0.0)
    assert np.allclose(sham.reserve_c, 1.0)
    assert np.allclose(sham.load_l, 0.0)


@pytest.mark.unit
def test_stress_panel_exports_all_arms_and_l3_to_l1_snapshots() -> None:
    panel = run_stress_allostatic_panel()
    assert panel["diagnostic_label_guard_enabled"] is True
    assert tuple(panel["arms"].keys()) == STRESS_ARM_IDS
    assert len(panel["l3_to_l1_coupling_snapshots"]) == 8
    for arm_id in STRESS_ARM_IDS:
        assert len(panel["trajectories"][arm_id]) == 97
