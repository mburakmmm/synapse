"""L2 dose-independent receptor-occupancy and synaptic conductance modulation models (RUO)."""

from __future__ import annotations

import hashlib
import json
import math
from itertools import pairwise
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

PHARMA_ARM_IDS: tuple[str, ...] = (
    "sham_zero_stimulus",
    "vehicle_baseline_40hz",
    "rdl_gaba_antag_50pct",
    "rdl_gaba_antag_100pct",
    "rdl_gaba_pam_175pct",
    "nachr_ach_atten_50pct",
    "combined_rdl_pam_plus_nachr_atten",
    "matched_ctrl_rdl_antag_100pct",
)


class ReceptorModulationParameters(BaseModel):
    """Immutable L2 parameter set for dose-independent Drosophila receptor modulation.

    Models normalized concentration-response curves using dimensionless affinity ratios
    (``[A]/EC50``, ``[B]/Ki``, ``[I]/IC50``, ``[M]/Km``) rather than named compound doses.
    ``named_compound_gate_enabled`` remains ``False`` per AGENTS.md section 10 until
    species-specific receptor, concentration, and kinetic evidence gates are explicitly
    satisfied.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "receptor_conductance_modulation_v1"
    model_revision: str = "1.0"
    model_level: Literal["L2"] = "L2"
    solver: Literal["analytic_hill_schild"] = "analytic_hill_schild"
    dt_s: float = 0.0
    named_compound_gate_enabled: bool = False

    rdl_gaba_a_hill_n: float = 1.6
    rdl_noncomp_ic50_norm: float = 1.0
    rdl_noncomp_floor: float = 0.0
    rdl_pam_km_norm: float = 1.0
    rdl_pam_hill_m: float = 1.2
    rdl_pam_max_gain: float = 2.0

    nachr_ach_hill_n: float = 1.3
    nachr_comp_ki_norm: float = 1.0
    nachr_noncomp_floor: float = 0.0

    grid_log10_min: float = -3.0
    grid_log10_max: float = 3.0
    grid_points: int = 46

    pilot_coupling_rdl_50pct_scale: float = 0.5
    pilot_coupling_rdl_100pct_scale: float = 0.0
    pilot_coupling_rdl_pam_scale: float = 1.75
    pilot_coupling_nachr_50pct_scale: float = 0.5

    parameter_source: str = (
        "Bliss (1939 Ann Appl Biol 10.1111/j.1744-7348.1939.tb06990.x); "
        "Arunlakshana & Schild (1959 Br J Pharmacol Chemother 10.1111/j.1476-5381.1959.tb00928.x); "
        "ffrench-Constant et al. (1993 Nature 10.1038/363449a0); "
        "Lee & O'Dowd (1999 J Neurosci 10.1523/JNEUROSCI.19-13-05311.1999); "
        "Su & O'Dowd (2003 J Neurosci 10.1523/JNEUROSCI.23-27-09246.2003); "
        "Buckingham & Sattelle (2005 Compr Mol Insect Sci 10.1016/B0-44-451924-6/00095-8); "
        "Liu et al. (2007 Neuron 10.1016/j.neuron.2007.10.036); "
        "Matsuda et al. (2020 Annu Rev Pharmacol Toxicol 10.1146/annurev-pharmtox-010818-021747)"
    )

    @model_validator(mode="after")
    def _validate_kinetics(self) -> ReceptorModulationParameters:
        if self.named_compound_gate_enabled:
            raise ValueError(
                "named_compound_gate_enabled must remain False for L2 dose-independent baseline"
            )
        strictly_positive = (
            ("rdl_gaba_a_hill_n", self.rdl_gaba_a_hill_n),
            ("rdl_noncomp_ic50_norm", self.rdl_noncomp_ic50_norm),
            ("rdl_pam_km_norm", self.rdl_pam_km_norm),
            ("rdl_pam_hill_m", self.rdl_pam_hill_m),
            ("nachr_ach_hill_n", self.nachr_ach_hill_n),
            ("nachr_comp_ki_norm", self.nachr_comp_ki_norm),
        )
        for name, value in strictly_positive:
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0, got {value}")
        for name, value in (
            ("rdl_noncomp_floor", self.rdl_noncomp_floor),
            ("nachr_noncomp_floor", self.nachr_noncomp_floor),
        ):
            if not math.isfinite(value) or not (0.0 <= value < 1.0):
                raise ValueError(f"{name} must lie in [0, 1), got {value}")
        if not math.isfinite(self.rdl_pam_max_gain) or self.rdl_pam_max_gain <= 1.0:
            raise ValueError(f"rdl_pam_max_gain must be > 1.0, got {self.rdl_pam_max_gain}")
        if self.grid_points < 15:
            raise ValueError(f"grid_points must be >= 15, got {self.grid_points}")
        if self.grid_log10_max <= self.grid_log10_min:
            raise ValueError("grid_log10_max must exceed grid_log10_min")
        if not (1.0 < self.pilot_coupling_rdl_pam_scale < self.rdl_pam_max_gain):
            raise ValueError(
                "pilot_coupling_rdl_pam_scale must lie strictly in (1.0, rdl_pam_max_gain)"
            )
        return self

    def canonical_sha256(self) -> str:
        """Compute deterministic SHA-256 hash of canonical parameter dictionary."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_non_negative(name: str, value: float) -> float:
    val = float(value)
    if not math.isfinite(val) or val < 0.0:
        raise ValueError(f"{name} must be finite and >= 0, got {value}")
    return val


def _validate_positive(name: str, value: float) -> float:
    val = float(value)
    if not math.isfinite(val) or val <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {value}")
    return val


def hill_occupancy(ratio_ec50: float, *, hill_n: float = 1.0) -> float:
    """Compute dimensionless Hill receptor occupancy in [0, 1].

    Args:
        ratio_ec50: Normalized agonist ratio ``[A] / EC50`` (>= 0).
        hill_n: Hill cooperativity coefficient (> 0).
    """
    x = _validate_non_negative("ratio_ec50", ratio_ec50)
    n = _validate_positive("hill_n", hill_n)
    if x == 0.0:
        return 0.0
    x_n = x**n
    return float(x_n / (1.0 + x_n))


def competitive_antagonist_response(
    agonist_ratio_ec50: float,
    antagonist_ratio_ki: float,
    *,
    hill_n: float = 1.0,
) -> float:
    """Compute competitive antagonist fractional response (Gaddum/Schild equation).

    A reversible competitive antagonist shifts apparent EC50 by the dose ratio
    ``DR = 1 + [B] / Ki`` without altering maximal efficacy (unit Schild slope).
    """
    x = _validate_non_negative("agonist_ratio_ec50", agonist_ratio_ec50)
    b = _validate_non_negative("antagonist_ratio_ki", antagonist_ratio_ki)
    n = _validate_positive("hill_n", hill_n)
    if x == 0.0:
        return 0.0
    x_n = x**n
    ec50_shifted_n = (1.0 + b) ** n
    return float(x_n / (ec50_shifted_n + x_n))


def noncompetitive_antagonist_conductance_scale(
    inhibitor_ratio_ic50: float,
    *,
    hill_n: float = 1.0,
    floor: float = 0.0,
) -> float:
    """Compute synaptic conductance scaling factor under noncompetitive channel block.

    Maps normalized inhibitor ratio ``[I] / IC50`` monotonically from ``1.0`` down to
    ``floor`` (``0.0`` represents complete pore block).
    """
    i_ratio = _validate_non_negative("inhibitor_ratio_ic50", inhibitor_ratio_ic50)
    n = _validate_positive("hill_n", hill_n)
    if not math.isfinite(floor) or not (0.0 <= floor <= 1.0):
        raise ValueError(f"floor must lie in [0, 1], got {floor}")
    if i_ratio == 0.0:
        return 1.0
    frac_open = 1.0 / (1.0 + (i_ratio**n))
    return float(floor + (1.0 - floor) * frac_open)


def allosteric_pam_conductance_scale(
    modulator_ratio_km: float,
    *,
    max_gain: float = 2.0,
    hill_m: float = 1.0,
) -> float:
    """Compute synaptic conductance gain under positive allosteric modulation (PAM).

    Maps normalized modulator ratio ``[M] / Km`` monotonically from ``1.0`` up to
    ``max_gain``.
    """
    m_ratio = _validate_non_negative("modulator_ratio_km", modulator_ratio_km)
    m = _validate_positive("hill_m", hill_m)
    if not math.isfinite(max_gain) or max_gain < 1.0:
        raise ValueError(f"max_gain must be finite and >= 1.0, got {max_gain}")
    if m_ratio == 0.0:
        return 1.0
    frac = (m_ratio**m) / (1.0 + (m_ratio**m))
    return float(1.0 + (max_gain - 1.0) * frac)


def bliss_independence_expected_suppression(suppression_a: float, suppression_b: float) -> float:
    """Compute Bliss independence expectation ``f_A + f_B - f_A * f_B`` in [0, 1]."""
    fa = float(suppression_a)
    fb = float(suppression_b)
    if not (math.isfinite(fa) and 0.0 <= fa <= 1.0):
        raise ValueError(f"suppression_a must lie in [0, 1], got {suppression_a}")
    if not (math.isfinite(fb) and 0.0 <= fb <= 1.0):
        raise ValueError(f"suppression_b must lie in [0, 1], got {suppression_b}")
    return float(fa + fb - fa * fb)


def _solve_competitive_ec50_ratio(antagonist_ratio_ki: float, *, hill_n: float) -> float:
    """Numerically verify half-maximal agonist ratio via bisection on [0.5, 100.0]."""
    low = 0.0
    high = max(2.0, 2.0 * (1.0 + antagonist_ratio_ki))
    for _ in range(80):
        mid = 0.5 * (low + high)
        val = competitive_antagonist_response(mid, antagonist_ratio_ki, hill_n=hill_n)
        if val < 0.5:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def verify_pharmacology_gates(
    params: ReceptorModulationParameters | None = None,
) -> dict[str, Any]:
    """Run quantitative verification gates for L2 receptor-conductance kinetics (RUO)."""
    cfg = params or ReceptorModulationParameters()

    # Gate 1: Hill boundary and half-maximal occupancy invariants
    hill_checks: list[dict[str, Any]] = []
    hill_passed = True
    for n_val in (1.0, cfg.nachr_ach_hill_n, cfg.rdl_gaba_a_hill_n):
        e0 = hill_occupancy(0.0, hill_n=n_val)
        ehalf = hill_occupancy(1.0, hill_n=n_val)
        ehigh = hill_occupancy(1.0e6, hill_n=n_val)
        ok = (abs(e0 - 0.0) < 1e-12) and (abs(ehalf - 0.5) < 1e-12) and (ehigh > 0.999999)
        hill_passed = hill_passed and ok
        hill_checks.append(
            {
                "hill_n": n_val,
                "occ_zero": e0,
                "occ_ec50": ehalf,
                "occ_1e6": ehigh,
                "passed": ok,
            }
        )

    # Gate 2: Arunlakshana-Schild regression slope == 1.0 for competitive nAChR antagonism
    b_ratios = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
    schild_points: list[dict[str, float]] = []
    max_dr_err = 0.0
    for b_rat in b_ratios:
        solved_ec50 = _solve_competitive_ec50_ratio(b_rat, hill_n=cfg.nachr_ach_hill_n)
        expected_dr = 1.0 + b_rat
        max_dr_err = max(max_dr_err, abs(solved_ec50 - expected_dr))
        schild_points.append(
            {
                "antagonist_ratio_ki": float(b_rat),
                "log10_antagonist_ratio": float(math.log10(b_rat)),
                "dose_ratio_numeric": float(solved_ec50),
                "dose_ratio_exact": float(expected_dr),
                "log10_dr_minus_1": float(math.log10(max(solved_ec50 - 1.0, 1e-15))),
            }
        )
    xs = np.array([p["log10_antagonist_ratio"] for p in schild_points], dtype=np.float64)
    ys = np.array([p["log10_dr_minus_1"] for p in schild_points], dtype=np.float64)
    slope, intercept = np.polyfit(xs, ys, 1)
    y_pred = slope * xs + intercept
    ss_res = float(np.sum((ys - y_pred) ** 2))
    ss_tot = float(np.sum((ys - float(np.mean(ys))) ** 2))
    r2 = 1.0 - (ss_res / ss_tot if ss_tot > 0.0 else 0.0)
    schild_passed = (abs(float(slope) - 1.0) < 1e-6) and (r2 > 0.999999) and (max_dr_err < 1e-6)

    # Gate 3: Noncompetitive antagonism vs PAM bidirectional monotonicity
    grid = np.logspace(cfg.grid_log10_min, cfg.grid_log10_max, cfg.grid_points)
    rdl_antag_vals = [
        noncompetitive_antagonist_conductance_scale(
            float(val),
            hill_n=cfg.rdl_gaba_a_hill_n,
            floor=cfg.rdl_noncomp_floor,
        )
        for val in grid
    ]
    rdl_pam_vals = [
        allosteric_pam_conductance_scale(
            float(val),
            max_gain=cfg.rdl_pam_max_gain,
            hill_m=cfg.rdl_pam_hill_m,
        )
        for val in grid
    ]
    antag_decreasing = all(a > b for a, b in pairwise(rdl_antag_vals))
    pam_increasing = all(a < b for a, b in pairwise(rdl_pam_vals))
    antag_half = noncompetitive_antagonist_conductance_scale(
        1.0, hill_n=cfg.rdl_gaba_a_hill_n, floor=cfg.rdl_noncomp_floor
    )
    pam_half = allosteric_pam_conductance_scale(
        1.0, max_gain=cfg.rdl_pam_max_gain, hill_m=cfg.rdl_pam_hill_m
    )
    expected_antag_half = 0.5 * (1.0 + cfg.rdl_noncomp_floor)
    expected_pam_half = 0.5 * (1.0 + cfg.rdl_pam_max_gain)
    bidirectional_passed = (
        antag_decreasing
        and pam_increasing
        and abs(antag_half - expected_antag_half) < 1e-12
        and abs(pam_half - expected_pam_half) < 1e-12
    )

    # Gate 4: Bliss independence algebraic identity
    b_half_half = bliss_independence_expected_suppression(0.5, 0.5)
    b_30_40 = bliss_independence_expected_suppression(0.3, 0.4)
    b_40_30 = bliss_independence_expected_suppression(0.4, 0.3)
    b_zero = bliss_independence_expected_suppression(0.42, 0.0)
    bliss_passed = (
        abs(b_half_half - 0.75) < 1e-12
        and abs(b_30_40 - 0.58) < 1e-12
        and abs(b_30_40 - b_40_30) < 1e-12
        and abs(b_zero - 0.42) < 1e-12
    )

    # Gate 5: Dose-independent mechanistic & RUO boundary check
    ruo_passed = (not cfg.named_compound_gate_enabled) and (cfg.model_level == "L2")

    overall_passed = (
        hill_passed and schild_passed and bidirectional_passed and bliss_passed and ruo_passed
    )
    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "solver": cfg.solver,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "overall_passed": bool(overall_passed),
        "gates": {
            "hill_boundary_and_half_max": {
                "passed": bool(hill_passed),
                "checks": hill_checks,
            },
            "schild_linearity_and_slope": {
                "passed": bool(schild_passed),
                "schild_slope": float(slope),
                "schild_intercept": float(intercept),
                "r_squared": float(r2),
                "max_dose_ratio_abs_error": float(max_dr_err),
                "points": schild_points,
            },
            "noncompetitive_vs_pam_directionality": {
                "passed": bool(bidirectional_passed),
                "antag_strictly_decreasing": bool(antag_decreasing),
                "pam_strictly_increasing": bool(pam_increasing),
                "antag_scale_at_ic50": float(antag_half),
                "pam_scale_at_km": float(pam_half),
            },
            "bliss_independence_identity": {
                "passed": bool(bliss_passed),
                "bliss_0_5_plus_0_5": float(b_half_half),
                "bliss_0_3_plus_0_4": float(b_30_40),
                "symmetry_abs_diff": float(abs(b_30_40 - b_40_30)),
            },
            "ruo_dose_independent_guard": {
                "passed": bool(ruo_passed),
                "named_compound_gate_enabled": bool(cfg.named_compound_gate_enabled),
                "unit_system": "dimensionless_affinity_ratios",
            },
        },
    }


def simulate_receptor_modulation_panel(
    params: ReceptorModulationParameters | None = None,
) -> dict[str, Any]:
    """Evaluate L2 dose-independent receptor-conductance curves and L2->L1 pilot snapshots."""
    cfg = params or ReceptorModulationParameters()
    grid = np.logspace(cfg.grid_log10_min, cfg.grid_log10_max, cfg.grid_points)

    rdl_antag_curve = [
        {
            "ratio_ic50": float(x),
            "log10_ratio": float(math.log10(x)),
            "conductance_scale": noncompetitive_antagonist_conductance_scale(
                float(x),
                hill_n=cfg.rdl_gaba_a_hill_n,
                floor=cfg.rdl_noncomp_floor,
            ),
        }
        for x in grid
    ]
    rdl_pam_curve = [
        {
            "ratio_km": float(x),
            "log10_ratio": float(math.log10(x)),
            "conductance_scale": allosteric_pam_conductance_scale(
                float(x),
                max_gain=cfg.rdl_pam_max_gain,
                hill_m=cfg.rdl_pam_hill_m,
            ),
        }
        for x in grid
    ]
    nachr_noncomp_curve = [
        {
            "ratio_ic50": float(x),
            "log10_ratio": float(math.log10(x)),
            "conductance_scale": noncompetitive_antagonist_conductance_scale(
                float(x),
                hill_n=cfg.nachr_ach_hill_n,
                floor=cfg.nachr_noncomp_floor,
            ),
        }
        for x in grid
    ]

    schild_antag_levels = (0.0, 1.0, 3.0, 10.0, 30.0)
    nachr_comp_curves = [
        {
            "antagonist_ratio_ki": float(b_rat),
            "expected_dose_ratio": float(1.0 + b_rat),
            "points": [
                {
                    "agonist_ratio_ec50": float(a_rat),
                    "log10_agonist_ratio": float(math.log10(a_rat)),
                    "response": competitive_antagonist_response(
                        float(a_rat),
                        float(b_rat),
                        hill_n=cfg.nachr_ach_hill_n,
                    ),
                }
                for a_rat in grid
            ],
        }
        for b_rat in schild_antag_levels
    ]

    bliss_levels = (0.0, 0.25, 0.50, 0.75, 1.0)
    bliss_grid = [
        {
            "suppression_a": float(fa),
            "suppression_b": float(fb),
            "expected_bliss_suppression": bliss_independence_expected_suppression(fa, fb),
        }
        for fa in bliss_levels
        for fb in bliss_levels
    ]

    # Solve exact [M]/Km corresponding to pilot_coupling_rdl_pam_scale (1.75x):
    # gamma = 1 + (max_gain - 1) * m^hill_m / (1 + m^hill_m)
    pam_frac = (cfg.pilot_coupling_rdl_pam_scale - 1.0) / (cfg.rdl_pam_max_gain - 1.0)
    pam_m_ratio = float((pam_frac / (1.0 - pam_frac)) ** (1.0 / cfg.rdl_pam_hill_m))

    l1_coupling_snapshots = [
        {
            "condition_id": "sham_zero_stimulus",
            "receptor_target": "none_sham",
            "mechanism": "negative_control",
            "normalized_ratio_label": "stim=0 Hz",
            "rdl_gaba_scale": 1.0,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "vehicle_baseline_40hz",
            "receptor_target": "none_vehicle",
            "mechanism": "baseline",
            "normalized_ratio_label": "[I]=0, [M]=0",
            "rdl_gaba_scale": 1.0,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "rdl_gaba_antag_50pct",
            "receptor_target": "Rdl (GABA_A)",
            "mechanism": "noncompetitive_antagonist",
            "normalized_ratio_label": "[I]/IC50 = 1.00",
            "rdl_gaba_scale": cfg.pilot_coupling_rdl_50pct_scale,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "rdl_gaba_antag_100pct",
            "receptor_target": "Rdl (GABA_A)",
            "mechanism": "noncompetitive_block_asymptote",
            "normalized_ratio_label": "[I]/IC50 -> inf",
            "rdl_gaba_scale": cfg.pilot_coupling_rdl_100pct_scale,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "rdl_gaba_pam_175pct",
            "receptor_target": "Rdl (GABA_A)",
            "mechanism": "positive_allosteric_modulator",
            "normalized_ratio_label": f"[M]/Km = {pam_m_ratio:.2f}",
            "rdl_gaba_scale": cfg.pilot_coupling_rdl_pam_scale,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "nachr_ach_atten_50pct",
            "receptor_target": "nAChR (ACH)",
            "mechanism": "noncompetitive_attenuation",
            "normalized_ratio_label": "[I]/IC50 = 1.00",
            "rdl_gaba_scale": 1.0,
            "nachr_ach_scale": cfg.pilot_coupling_nachr_50pct_scale,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "combined_rdl_pam_plus_nachr_atten",
            "receptor_target": "Rdl (GABA_A) + nAChR (ACH)",
            "mechanism": "dual_target_bliss_test",
            "normalized_ratio_label": f"[M]/Km = {pam_m_ratio:.2f} + [I]/IC50 = 1.00",
            "rdl_gaba_scale": cfg.pilot_coupling_rdl_pam_scale,
            "nachr_ach_scale": cfg.pilot_coupling_nachr_50pct_scale,
            "matched_ctrl_rdl_scale": 1.0,
        },
        {
            "condition_id": "matched_ctrl_rdl_antag_100pct",
            "receptor_target": "Rdl (matched VNC GABA off-pathway)",
            "mechanism": "matched_control_specificity",
            "normalized_ratio_label": "[I]/IC50 -> inf (off-pathway)",
            "rdl_gaba_scale": 1.0,
            "nachr_ach_scale": 1.0,
            "matched_ctrl_rdl_scale": 0.0,
        },
    ]

    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "solver": cfg.solver,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "named_compound_gate_enabled": bool(cfg.named_compound_gate_enabled),
        "rdl_gaba_a_noncomp_curve": rdl_antag_curve,
        "rdl_gaba_a_pam_curve": rdl_pam_curve,
        "nachr_ach_noncomp_curve": nachr_noncomp_curve,
        "nachr_ach_comp_curves": nachr_comp_curves,
        "bliss_surface_grid": bliss_grid,
        "l1_coupling_snapshots": l1_coupling_snapshots,
    }
