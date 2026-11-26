"""Unit tests for Phase 5C-2 L2 dose-independent receptor kinetics (RUO)."""

from __future__ import annotations

import math

import pytest

from synapse_core import (
    PHARMA_ARM_IDS,
    ReceptorModulationParameters,
    allosteric_pam_conductance_scale,
    bliss_independence_expected_suppression,
    competitive_antagonist_response,
    hill_occupancy,
    noncompetitive_antagonist_conductance_scale,
    simulate_receptor_modulation_panel,
    verify_pharmacology_gates,
)


@pytest.mark.unit
def test_pharmacology_gate_suite_passes_all_five_invariants() -> None:
    params = ReceptorModulationParameters()
    report = verify_pharmacology_gates(params)
    assert report["overall_passed"] is True
    assert report["model_level"] == "L2"
    assert report["solver"] == "analytic_hill_schild"
    assert len(report["gates"]) == 5
    for gate in report["gates"].values():
        assert gate["passed"] is True

    schild = report["gates"]["schild_linearity_and_slope"]
    assert abs(schild["schild_slope"] - 1.0) < 1e-6
    assert schild["r_squared"] > 0.999999
    assert schild["max_dose_ratio_abs_error"] < 1e-6


@pytest.mark.unit
def test_receptor_equations_boundaries_and_monotonicity() -> None:
    assert hill_occupancy(0.0, hill_n=1.6) == 0.0
    assert math.isclose(hill_occupancy(1.0, hill_n=1.6), 0.5, rel_tol=0.0, abs_tol=1e-12)
    assert hill_occupancy(1000.0, hill_n=1.6) > 0.9999

    assert competitive_antagonist_response(0.0, 3.0, hill_n=1.3) == 0.0
    assert math.isclose(
        competitive_antagonist_response(4.0, 3.0, hill_n=1.3),
        0.5,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    assert noncompetitive_antagonist_conductance_scale(0.0, hill_n=1.6) == 1.0
    assert math.isclose(
        noncompetitive_antagonist_conductance_scale(1.0, hill_n=1.6),
        0.5,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert noncompetitive_antagonist_conductance_scale(1.0e4, hill_n=1.6) < 1e-6

    assert allosteric_pam_conductance_scale(0.0, max_gain=2.0, hill_m=1.2) == 1.0
    assert math.isclose(
        allosteric_pam_conductance_scale(1.0, max_gain=2.0, hill_m=1.2),
        1.5,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        allosteric_pam_conductance_scale(3.0 ** (1.0 / 1.2), max_gain=2.0, hill_m=1.2),
        1.75,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    assert math.isclose(
        bliss_independence_expected_suppression(0.5, 0.5),
        0.75,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        bliss_independence_expected_suppression(0.3, 0.4),
        0.58,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


@pytest.mark.unit
def test_pharmacology_ruo_guard_and_panel_coupling() -> None:
    with pytest.raises(ValueError, match="named_compound_gate_enabled"):
        ReceptorModulationParameters(named_compound_gate_enabled=True)

    with pytest.raises(ValueError):
        hill_occupancy(-0.1)

    with pytest.raises(ValueError):
        bliss_independence_expected_suppression(1.2, 0.1)

    panel = simulate_receptor_modulation_panel()
    assert panel["named_compound_gate_enabled"] is False
    assert len(panel["rdl_gaba_a_noncomp_curve"]) == 46
    assert len(panel["rdl_gaba_a_pam_curve"]) == 46
    assert len(panel["nachr_ach_comp_curves"]) == 5
    snapshots = panel["l1_coupling_snapshots"]
    assert tuple(row["condition_id"] for row in snapshots) == PHARMA_ARM_IDS
