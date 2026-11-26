"""L3 Drosophila reactive-scope allostatic load & defensive arousal ODEs (RUO)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.integrate import solve_ivp

STRESS_ARM_IDS: tuple[str, ...] = (
    "sham_zero_stressor",
    "acute_single_threat",
    "chronic_repeated_stress",
    "chronic_with_washout_recovery",
)

STATE_NAMES: tuple[str, ...] = ("arousal_a", "reserve_c", "load_l")
DEFAULT_Y0: tuple[float, float, float] = (0.0, 1.0, 0.0)


class StressAllostaticParameters(BaseModel):
    """Immutable L3 parameter set for reactive-scope defensive arousal & allostatic load.

    Models three coupled macro-states on an hours timescale:
    - ``A in [0, 1]``: defensive threat-arousal proxy driven by visual/mechanical stressor ``u(t)``
    - ``C in [c_min, 1]``: inhibitory reactive-scope reserve providing homeostatic feedback
    - ``L >= 0``: cumulative allostatic wear amplified when reserve ``C`` erodes

    ``diagnostic_label_guard_enabled`` remains ``True`` per ``AGENTS.md`` sections 1 and 10:
    outcomes represent fly-level defensive arousal/allostasis proxies only, never human clinical
    anxiety or depression diagnoses.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "stress_allostatic_reactive_scope_v1"
    model_revision: str = "1.0"
    model_level: Literal["L3"] = "L3"
    solver: Literal["RK45"] = "RK45"

    dt_eval_h: float = 0.05
    seconds_per_hour: float = 3600.0
    duration_h: float = 48.0
    diagnostic_label_guard_enabled: bool = True

    k_drive: float = 5.0
    tau_a_h: float = 0.5
    k_fb: float = 2.5

    tau_c_h: float = 14.0
    k_wear: float = 1.1
    a_thresh: float = 0.25
    c_min: float = 0.2

    k_load: float = 0.6
    load_wear_amp: float = 1.5
    tau_l_h: float = 24.0
    ramp_h: float = 0.15

    parameter_source: str = (
        "McEwen (1998 NEJM 10.1056/NEJM199801153380307); "
        "Romero, Dickens & Cyr (2009 Horm Behav 10.1016/j.yhbeh.2008.12.009); "
        "Gibson et al. (2015 Curr Biol 10.1016/j.cub.2015.03.058); "
        "Ries et al. (2017 Nat Commun 10.1038/ncomms15738); "
        "von Reyn et al. (2017 Neuron 10.1016/j.neuron.2017.05.036); "
        "Zacarias et al. (2018 Nat Commun 10.1038/s41467-018-05875-1); "
        "Ache et al. (2019 Curr Biol 10.1016/j.cub.2019.01.079); "
        "Nassel & Zandawala (2019 Prog Neurobiol 10.1016/j.pneurobio.2019.02.003)"
    )

    @model_validator(mode="after")
    def _validate_bounds(self) -> StressAllostaticParameters:
        if not self.diagnostic_label_guard_enabled:
            raise ValueError(
                "diagnostic_label_guard_enabled must remain True (no human diagnostic labels)"
            )
        strictly_positive = (
            ("dt_eval_h", self.dt_eval_h),
            ("seconds_per_hour", self.seconds_per_hour),
            ("duration_h", self.duration_h),
            ("k_drive", self.k_drive),
            ("tau_a_h", self.tau_a_h),
            ("k_fb", self.k_fb),
            ("tau_c_h", self.tau_c_h),
            ("k_wear", self.k_wear),
            ("k_load", self.k_load),
            ("tau_l_h", self.tau_l_h),
            ("ramp_h", self.ramp_h),
        )
        for name, value in strictly_positive:
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0, got {value}")
        if not math.isfinite(self.a_thresh) or not (0.0 <= self.a_thresh < 1.0):
            raise ValueError(f"a_thresh must lie in [0, 1), got {self.a_thresh}")
        if not math.isfinite(self.c_min) or not (0.0 <= self.c_min < 1.0):
            raise ValueError(f"c_min must lie in [0, 1), got {self.c_min}")
        if not math.isfinite(self.load_wear_amp) or self.load_wear_amp < 0.0:
            raise ValueError(f"load_wear_amp must be finite and >= 0, got {self.load_wear_amp}")
        return self

    def canonical_sha256(self) -> str:
        """Compute deterministic SHA-256 hash of canonical parameter dictionary."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StressTrajectory:
    """Evaluated trajectory for one L3 stress-allostatic experimental arm."""

    arm_id: str
    time_h: np.ndarray
    arousal_a: np.ndarray
    reserve_c: np.ndarray
    load_l: np.ndarray
    stressor_u: np.ndarray


def _smooth_pulse(t_h: float, start_h: float, end_h: float, ramp_h: float) -> float:
    """C1 cubic Hermite boxcar pulse on [start_h, end_h] for numerical RK45 stability."""
    if t_h <= start_h or t_h >= end_h:
        return 0.0
    r = min(ramp_h, 0.45 * (end_h - start_h))
    if r <= 0.0:
        return 1.0
    if t_h < start_h + r:
        s = (t_h - start_h) / r
        return float(s * s * (3.0 - 2.0 * s))
    if t_h > end_h - r:
        s = (end_h - t_h) / r
        return float(s * s * (3.0 - 2.0 * s))
    return 1.0


def _stressor_windows(arm_id: str) -> list[tuple[float, float]]:
    if arm_id == "sham_zero_stressor":
        return []
    if arm_id == "acute_single_threat":
        return [(4.0, 4.5)]
    if arm_id == "chronic_repeated_stress":
        return [(4.0 + 2.0 * k, 5.0 + 2.0 * k) for k in range(18)]
    if arm_id == "chronic_with_washout_recovery":
        return [(4.0 + 2.0 * k, 5.0 + 2.0 * k) for k in range(9)]
    raise ValueError(f"Unknown stress arm_id: {arm_id!r}")


def stressor_intensity(arm_id: str, t_h: float, params: StressAllostaticParameters) -> float:
    """Evaluate bounded stressor drive u(t) in [0, 1] at time t_h (hours)."""
    windows = _stressor_windows(arm_id)
    if not windows:
        return 0.0
    val = 0.0
    for start_h, end_h in windows:
        val = max(val, _smooth_pulse(t_h, start_h, end_h, params.ramp_h))
    return float(val)


def simulate_stress_schedule(
    arm_id: str,
    params: StressAllostaticParameters | None = None,
    *,
    rtol: float = 1e-7,
    atol: float = 1e-10,
    max_step_h: float = 0.05,
) -> StressTrajectory:
    """Integrate the L3 reactive-scope stress-allostatic ODEs via RK45."""
    cfg = params or StressAllostaticParameters()
    if arm_id not in STRESS_ARM_IDS:
        raise ValueError(f"arm_id must be one of {STRESS_ARM_IDS}, got {arm_id!r}")

    n_steps = round(cfg.duration_h / cfg.dt_eval_h) + 1
    t_eval = np.linspace(0.0, cfg.duration_h, n_steps, dtype=np.float64)

    def _rhs(t: float, y: np.ndarray) -> list[float]:
        a_val = float(np.clip(y[0], 0.0, 1.0))
        c_val = float(np.clip(y[1], cfg.c_min, 1.0))
        l_val = max(0.0, float(y[2]))
        u_t = stressor_intensity(arm_id, float(t), cfg)

        da = cfg.k_drive * u_t * (1.0 - a_val) - ((1.0 + cfg.k_fb * c_val) / cfg.tau_a_h) * a_val
        excess = max(0.0, a_val - cfg.a_thresh)
        dc = ((1.0 - c_val) / cfg.tau_c_h) - cfg.k_wear * excess * (c_val - cfg.c_min)
        dl = cfg.k_load * excess * (1.0 + cfg.load_wear_amp * (1.0 - c_val)) - (l_val / cfg.tau_l_h)
        return [da, dc, dl]

    sol = solve_ivp(
        _rhs,
        (0.0, cfg.duration_h),
        list(DEFAULT_Y0),
        method="RK45",
        t_eval=t_eval,
        rtol=rtol,
        atol=atol,
        max_step=max_step_h,
    )
    if not sol.success:
        raise RuntimeError(f"RK45 integration failed for {arm_id}: {sol.message}")

    u_arr = np.array([stressor_intensity(arm_id, float(t), cfg) for t in t_eval], dtype=np.float64)
    return StressTrajectory(
        arm_id=arm_id,
        time_h=sol.t.copy(),
        arousal_a=sol.y[0].copy(),
        reserve_c=sol.y[1].copy(),
        load_l=sol.y[2].copy(),
        stressor_u=u_arr,
    )


def verify_stress_allostatic_gates(
    params: StressAllostaticParameters | None = None,
) -> dict[str, Any]:
    """Run all five L3 quantitative verification gates for stress-allostatic dynamics (RUO)."""
    cfg = params or StressAllostaticParameters()

    sham = simulate_stress_schedule("sham_zero_stressor", cfg)
    acute = simulate_stress_schedule("acute_single_threat", cfg)
    chronic = simulate_stress_schedule("chronic_repeated_stress", cfg)
    chronic_fine = simulate_stress_schedule(
        "chronic_repeated_stress", cfg, rtol=1e-9, atol=1e-12, max_step_h=0.01
    )
    washout = simulate_stress_schedule("chronic_with_washout_recovery", cfg)

    # Gate 1: RK45 step-size / tolerance convergence & biophysical state bounds
    diff_a = float(np.max(np.abs(chronic.arousal_a - chronic_fine.arousal_a)))
    diff_c = float(np.max(np.abs(chronic.reserve_c - chronic_fine.reserve_c)))
    diff_l = float(np.max(np.abs(chronic.load_l - chronic_fine.load_l)))
    max_abs_diff = max(diff_a, diff_c, diff_l)
    bounds_ok = all(
        (float(np.min(tr.arousal_a)) >= -1e-6)
        and (float(np.max(tr.arousal_a)) <= 1.0 + 1e-6)
        and (float(np.min(tr.reserve_c)) >= cfg.c_min - 1e-6)
        and (float(np.max(tr.reserve_c)) <= 1.0 + 1e-6)
        and (float(np.min(tr.load_l)) >= -1e-6)
        for tr in (sham, acute, chronic, washout)
    )
    gate1_ok = (max_abs_diff < 1e-4) and bounds_ok

    # Gate 2: Zero-stressor sham baseline invariance
    sham_max_a = float(np.max(np.abs(sham.arousal_a)))
    sham_max_c_dev = float(np.max(np.abs(sham.reserve_c - 1.0)))
    sham_max_l = float(np.max(np.abs(sham.load_l)))
    gate2_ok = (sham_max_a < 1e-12) and (sham_max_c_dev < 1e-12) and (sham_max_l < 1e-12)

    # Gate 3: Acute single-bout response, habituation/return to baseline, reserve preserved
    acute_a_peak = float(np.max(acute.arousal_a))
    acute_c_min = float(np.min(acute.reserve_c))
    acute_l_peak = float(np.max(acute.load_l))
    acute_a_end = float(acute.arousal_a[-1])
    gate3_ok = (acute_a_peak > 0.35) and (acute_c_min > 0.80) and (acute_a_end < 0.01)

    # Gate 4: Chronic repeated overload (reserve depletion, >=3x load, arousal sensitization)
    chronic_c_min = float(np.min(chronic.reserve_c))
    chronic_l_peak = float(np.max(chronic.load_l))
    bout1_mask = (chronic.time_h >= 4.0) & (chronic.time_h <= 5.5)
    bout18_mask = (chronic.time_h >= 38.0) & (chronic.time_h <= 39.5)
    a_first_peak = float(np.max(chronic.arousal_a[bout1_mask]))
    a_late_peak = float(np.max(chronic.arousal_a[bout18_mask]))
    load_ratio = chronic_l_peak / max(acute_l_peak, 1e-12)
    gate4_ok = (chronic_c_min < 0.65) and (load_ratio > 3.0) and (a_late_peak > a_first_peak + 0.05)

    # Gate 5: Post-chronic washout recovery & RUO non-clinical guard
    idx_21h = int(np.argmin(np.abs(washout.time_h - 21.0)))
    c_at_21h = float(washout.reserve_c[idx_21h])
    c_end_washout = float(washout.reserve_c[-1])
    l_peak_washout = float(np.max(washout.load_l))
    l_end_washout = float(washout.load_l[-1])
    gate5_ok = (
        (c_end_washout > c_at_21h + 0.15)
        and (l_end_washout < 0.5 * l_peak_washout)
        and cfg.diagnostic_label_guard_enabled
    )

    overall_passed = gate1_ok and gate2_ok and gate3_ok and gate4_ok and gate5_ok
    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "solver": cfg.solver,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "overall_passed": bool(overall_passed),
        "gates": {
            "rk45_convergence_and_bounds": {
                "passed": bool(gate1_ok),
                "max_abs_diff": float(max_abs_diff),
                "bounds_preserved": bool(bounds_ok),
            },
            "sham_baseline_invariance": {
                "passed": bool(gate2_ok),
                "sham_max_a": sham_max_a,
                "sham_max_c_dev": sham_max_c_dev,
                "sham_max_l": sham_max_l,
            },
            "acute_stress_habituation_and_recovery": {
                "passed": bool(gate3_ok),
                "acute_a_peak": acute_a_peak,
                "acute_c_min": acute_c_min,
                "acute_l_peak": acute_l_peak,
                "acute_a_end": acute_a_end,
            },
            "chronic_allostatic_overload_separation": {
                "passed": bool(gate4_ok),
                "chronic_c_min": chronic_c_min,
                "chronic_l_peak": chronic_l_peak,
                "chronic_vs_acute_load_ratio": float(load_ratio),
                "first_bout_a_peak": a_first_peak,
                "late_bout_a_peak": a_late_peak,
            },
            "post_chronic_washout_and_ruo_guard": {
                "passed": bool(gate5_ok),
                "washout_c_at_21h": c_at_21h,
                "washout_c_end": c_end_washout,
                "washout_l_peak": l_peak_washout,
                "washout_l_end": l_end_washout,
                "diagnostic_label_guard_enabled": bool(cfg.diagnostic_label_guard_enabled),
            },
        },
    }


def run_stress_allostatic_panel(
    params: StressAllostaticParameters | None = None,
) -> dict[str, Any]:
    """Run all 4 L3 stress-allostatic arms and export L3->L1 pilot coupling snapshots."""
    cfg = params or StressAllostaticParameters()
    trajectories = {arm_id: simulate_stress_schedule(arm_id, cfg) for arm_id in STRESS_ARM_IDS}

    arm_summaries: dict[str, dict[str, float | str]] = {}
    downsampled_trajectories: dict[str, list[dict[str, float]]] = {}
    stride = max(1, round(0.5 / cfg.dt_eval_h))

    for arm_id, tr in trajectories.items():
        arm_summaries[arm_id] = {
            "arm_id": arm_id,
            "duration_h": float(cfg.duration_h),
            "arousal_a_peak": float(np.max(tr.arousal_a)),
            "arousal_a_end": float(tr.arousal_a[-1]),
            "reserve_c_min": float(np.min(tr.reserve_c)),
            "reserve_c_end": float(tr.reserve_c[-1]),
            "load_l_peak": float(np.max(tr.load_l)),
            "load_l_end": float(tr.load_l[-1]),
        }
        pts: list[dict[str, float]] = []
        for idx in range(0, len(tr.time_h), stride):
            pts.append(
                {
                    "time_h": float(tr.time_h[idx]),
                    "arousal_a": float(tr.arousal_a[idx]),
                    "reserve_c": float(tr.reserve_c[idx]),
                    "load_l": float(tr.load_l[idx]),
                    "stressor_u": float(tr.stressor_u[idx]),
                }
            )
        downsampled_trajectories[arm_id] = pts

    chronic_c_min = float(arm_summaries["chronic_repeated_stress"]["reserve_c_min"])
    acute_a_peak = float(arm_summaries["acute_single_threat"]["arousal_a_peak"])
    chronic_a_peak = float(arm_summaries["chronic_repeated_stress"]["arousal_a_peak"])
    sensitization_ratio = round(chronic_a_peak / max(acute_a_peak, 1e-6), 3)

    l3_to_l1_coupling_snapshots = [
        {
            "condition_id": "sham_zero_stimulus",
            "l3_state_source": "sham_zero_stressor",
            "threat_drive_hz": 0.0,
            "inhibitory_reserve_scale": 1.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "Zero-stressor negative control (expected 0 spikes)",
        },
        {
            "condition_id": "acute_threat_baseline_30hz",
            "l3_state_source": "acute_single_threat (intact reserve C~1.0)",
            "threat_drive_hz": 30.0,
            "inhibitory_reserve_scale": 1.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": f"Acute bout A_peak={acute_a_peak:.3f}, intact C",
        },
        {
            "condition_id": "acute_threat_high_60hz",
            "l3_state_source": "acute_single_threat (doubled threat rate)",
            "threat_drive_hz": 60.0,
            "inhibitory_reserve_scale": 1.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "Threat-intensity ceiling reference onto LC4 + LC9",
        },
        {
            "condition_id": "chronic_allostatic_reserve_drop",
            "l3_state_source": f"chronic_repeated_stress (C_min={chronic_c_min:.3f})",
            "threat_drive_hz": 30.0,
            "inhibitory_reserve_scale": 0.5,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "50% defensive inhibitory reserve attenuation (GABA/GLUT -> DNs)",
        },
        {
            "condition_id": "chronic_allostatic_reserve_depletion",
            "l3_state_source": "chronic_repeated_stress (maximal reserve loss)",
            "threat_drive_hz": 30.0,
            "inhibitory_reserve_scale": 0.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "100% focal block of defensive inhibitory gate -> DNp01/DNp09",
        },
        {
            "condition_id": "chronic_arousal_sensory_sensitization",
            "l3_state_source": f"chronic_repeated_stress (A_late/A_1={sensitization_ratio:.2f}x)",
            "threat_drive_hz": 30.0,
            "inhibitory_reserve_scale": 0.5,
            "sensory_sensitization_scale": 1.4,
            "specificity_note": "Combined 0.5x inhibitory reserve drop + 1.4x LC4/LC9 gain",
        },
        {
            "condition_id": "matched_ctrl_nondefensive_visual_60hz",
            "l3_state_source": "specificity_control (non-defensive LC12 visual)",
            "threat_drive_hz": 60.0,
            "inhibitory_reserve_scale": 1.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "40 Hungarian-matched LC12 neurons (0 edges to DNp01/09/11)",
        },
        {
            "condition_id": "matched_ctrl_offpathway_inh_depletion",
            "l3_state_source": "specificity_control (off-pathway GABA/GLUT loss)",
            "threat_drive_hz": 30.0,
            "inhibitory_reserve_scale": 0.0,
            "sensory_sensitization_scale": 1.0,
            "specificity_note": "100% loss on 30 matched off-pathway GABA/GLUT interneurons",
        },
    ]

    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "solver": cfg.solver,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "diagnostic_label_guard_enabled": bool(cfg.diagnostic_label_guard_enabled),
        "arms": arm_summaries,
        "trajectories": downsampled_trajectories,
        "l3_to_l1_coupling_snapshots": l3_to_l1_coupling_snapshots,
    }
