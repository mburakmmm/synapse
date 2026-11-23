"""L3 Drosophila circadian molecular clock (Leloup & Goldbeter 1998) and two-process homeostat."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.integrate import solve_ivp

# Steady limit-cycle seed for BIOMD0000000021 (M_P, P0, P1, P2, M_T, T0, T1, T2, C, C_N) in nM
DEFAULT_Y0: tuple[float, ...] = (0.09, 0.02, 0.02, 0.01, 1.41, 0.54, 0.79, 4.65, 0.18, 1.20)
STATE_NAMES: tuple[str, ...] = ("M_P", "P0", "P1", "P2", "M_T", "T0", "T1", "T2", "C", "C_N")


class CircadianHomeostaticParameters(BaseModel):
    """Immutable SI/biochemical parameter set for coupled L3 circadian + Process S dynamics.

    Units are hours (``h``) and nanomolar (``nM``) for molecular PER/TIM ODEs matching
    Leloup & Goldbeter (1998, BIOMD0000000021), plus dimensionless normalized homeostatic
    pressure ``S in [s_min, s_max]`` using Drosophila LD time constants from
    Abhilash & Shafer (2024, Sleep zsad277).
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "leloup_goldbeter_1998_two_process_v1"
    model_revision: str = "1.0"
    model_level: Literal["L3"] = "L3"

    # PER / TIM transcription, translation, and mRNA degradation (nM, h)
    v_sP: float = 1.0
    v_sT: float = 1.0
    v_mP: float = 0.7
    v_mT: float = 0.7
    K_mP: float = 0.2
    K_mT: float = 0.2
    k_sP: float = 0.9
    k_sT: float = 0.9
    K_IP: float = 1.0
    K_IT: float = 1.0
    n_hill: float = 4.0

    # Phosphorylation / dephosphorylation cascade
    V_1P: float = 8.0
    V_2P: float = 1.0
    V_3P: float = 8.0
    V_4P: float = 1.0
    K_1P: float = 2.0
    K_2P: float = 2.0
    K_3P: float = 2.0
    K_4P: float = 2.0
    V_1T: float = 8.0
    V_2T: float = 1.0
    V_3T: float = 8.0
    V_4T: float = 1.0
    K_1T: float = 2.0
    K_2T: float = 2.0
    K_3T: float = 2.0
    K_4T: float = 2.0

    # Protein degradation & light-dependent TIM degradation
    v_dP: float = 2.0
    v_dT_dark: float = 2.0
    v_dT_light: float = 4.0
    K_dP: float = 0.2
    K_dT: float = 0.2
    k_d: float = 0.01
    k_dC: float = 0.01
    k_dN: float = 0.01

    # Complex association/dissociation and nucleocytoplasmic transport
    k1: float = 0.6
    k2: float = 0.2
    k3: float = 1.2
    k4: float = 0.6

    # Homeostatic Process S (Abhilash & Shafer 2024, Sleep; Daan et al. 1984)
    tau_i_h: float = 8.76
    tau_d_h: float = 9.51
    s_min: float = 0.0
    s_max: float = 1.0
    s_init: float = 0.45
    u_mean: float = 0.65
    l_mean: float = 0.35
    a_c: float = 0.12
    cn_mid: float = 1.15
    cn_half: float = 0.70

    # Numerical solver controls (Explicit ODE tolerances & timescale bridge)
    solver: Literal["RK45", "Radau"] = "RK45"
    dt_eval_h: float = 0.05
    max_step_h: float = 0.1
    rtol: float = 1e-8
    atol: float = 1e-10
    seconds_per_hour: float = 3600.0
    parameter_source: str = (
        "Leloup & Goldbeter (1998, J Biol Rhythms 13:70-87, BIOMD0000000021); "
        "Abhilash & Shafer (2024, Sleep zsad277, Drosophila tau_i=8.76h, tau_d=9.51h); "
        "Daan, Beersma & Borbely (1984, Am J Physiol)"
    )

    @model_validator(mode="after")
    def _validate_bounds(self) -> CircadianHomeostaticParameters:
        strictly_positive = (
            "K_mP",
            "K_mT",
            "K_IP",
            "K_IT",
            "n_hill",
            "K_1P",
            "K_2P",
            "K_3P",
            "K_4P",
            "K_1T",
            "K_2T",
            "K_3T",
            "K_4T",
            "K_dP",
            "K_dT",
            "tau_i_h",
            "tau_d_h",
            "cn_half",
            "dt_eval_h",
            "max_step_h",
            "rtol",
            "atol",
            "seconds_per_hour",
        )
        non_negative = (
            "v_sP",
            "v_sT",
            "v_mP",
            "v_mT",
            "k_sP",
            "k_sT",
            "V_1P",
            "V_2P",
            "V_3P",
            "V_4P",
            "V_1T",
            "V_2T",
            "V_3T",
            "V_4T",
            "v_dP",
            "v_dT_dark",
            "v_dT_light",
            "k_d",
            "k_dC",
            "k_dN",
            "k1",
            "k2",
            "k3",
            "k4",
            "a_c",
        )
        for field_name in (
            strictly_positive
            + non_negative
            + ("s_min", "s_max", "s_init", "u_mean", "l_mean", "cn_mid")
        ):
            val = float(getattr(self, field_name))
            if not math.isfinite(val):
                raise ValueError(f"{field_name} must be finite, got {val!r}")
        for field_name in strictly_positive:
            if float(getattr(self, field_name)) <= 0.0:
                raise ValueError(f"{field_name} must be strictly positive")
        for field_name in non_negative:
            if float(getattr(self, field_name)) < 0.0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.s_max <= self.s_min:
            raise ValueError("s_max must exceed s_min")
        if not (self.s_min <= self.s_init <= self.s_max):
            raise ValueError("s_init must lie within [s_min, s_max]")
        if not (self.s_min <= self.l_mean < self.u_mean <= self.s_max):
            raise ValueError("Thresholds must satisfy s_min <= l_mean < u_mean <= s_max")
        return self

    def canonical_sha256(self) -> str:
        """Compute deterministic SHA-256 digest of the canonical parameter manifest."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TwoProcessTrajectory:
    """Simulated coupled L3 molecular circadian and Process S homeostatic trajectory."""

    times_h: np.ndarray
    light: np.ndarray
    y: np.ndarray
    p_total: np.ndarray
    t_total: np.ndarray
    c_n: np.ndarray
    c_wake: np.ndarray
    u_threshold: np.ndarray
    l_threshold: np.ndarray
    s_homeostat: np.ndarray
    modeled_rest_state: (
        np.ndarray
    )  # 0 = wake_proxy, 1 = quiescence_rest_proxy (not validated behavioral sleep)
    deprivation_mask: np.ndarray


def wrap_phase_hours(delta_h: float, period_h: float) -> float:
    """Wrap a time/phase difference symmetrically into ``[-period_h/2, +period_h/2)``."""
    if period_h <= 0.0:
        raise ValueError("period_h must be > 0")
    half = 0.5 * period_h
    return float(((delta_h + half) % period_h) - half)


def detect_oscillation_peaks(
    times_h: np.ndarray,
    signal: np.ndarray,
    *,
    min_time_h: float = 48.0,
) -> np.ndarray:
    """Detect local oscillation peaks with 3-point parabolic sub-step refinement."""
    t_arr = np.asarray(times_h, dtype=np.float64)
    s_arr = np.asarray(signal, dtype=np.float64)
    if t_arr.ndim != 1 or s_arr.ndim != 1 or t_arr.size != s_arr.size:
        raise ValueError("times_h and signal must be 1-D arrays of equal length")
    if t_arr.size < 3:
        return np.empty(0, dtype=np.float64)

    peaks: list[float] = []
    for idx in range(1, s_arr.size - 1):
        if t_arr[idx] < min_time_h:
            continue
        y0, y1, y2 = float(s_arr[idx - 1]), float(s_arr[idx]), float(s_arr[idx + 1])
        if y1 > y0 and y1 >= y2 and (y1 > y0 or y1 > y2):
            denom = y0 - 2.0 * y1 + y2
            dt_local = float(t_arr[idx + 1] - t_arr[idx - 1]) * 0.5
            offset = 0.0
            if denom < -1e-12:
                raw_offset = 0.5 * (y0 - y2) / denom
                offset = float(np.clip(raw_offset, -0.5, 0.5)) * dt_local
            peaks.append(float(t_arr[idx] + offset))
    return np.asarray(peaks, dtype=np.float64)


def _leloup_goldbeter_rhs(
    t: float,
    y: Sequence[float],
    params: CircadianHomeostaticParameters,
    light_schedule: Callable[[float], float],
) -> list[float]:
    m_p, p0, p1, p2, m_t, t0, t1, t2, c_cyto, c_nuc = y
    light_level = float(np.clip(float(light_schedule(float(t))), 0.0, 1.0))
    v_dt = params.v_dT_dark + (params.v_dT_light - params.v_dT_dark) * light_level

    cn_pow = max(c_nuc, 0.0) ** params.n_hill
    kip_pow = params.K_IP**params.n_hill
    kit_pow = params.K_IT**params.n_hill

    dm_p = (
        params.v_sP * (kip_pow / (kip_pow + cn_pow))
        - params.v_mP * (m_p / (params.K_mP + m_p))
        - params.k_d * m_p
    )
    dp0 = (
        params.k_sP * m_p
        - params.V_1P * (p0 / (params.K_1P + p0))
        + params.V_2P * (p1 / (params.K_2P + p1))
        - params.k_d * p0
    )
    dp1 = (
        params.V_1P * (p0 / (params.K_1P + p0))
        - params.V_2P * (p1 / (params.K_2P + p1))
        - params.V_3P * (p1 / (params.K_3P + p1))
        + params.V_4P * (p2 / (params.K_4P + p2))
        - params.k_d * p1
    )
    dp2 = (
        params.V_3P * (p1 / (params.K_3P + p1))
        - params.V_4P * (p2 / (params.K_4P + p2))
        - params.k3 * p2 * t2
        + params.k4 * c_cyto
        - params.v_dP * (p2 / (params.K_dP + p2))
        - params.k_d * p2
    )

    dm_t = (
        params.v_sT * (kit_pow / (kit_pow + cn_pow))
        - params.v_mT * (m_t / (params.K_mT + m_t))
        - params.k_d * m_t
    )
    dt0 = (
        params.k_sT * m_t
        - params.V_1T * (t0 / (params.K_1T + t0))
        + params.V_2T * (t1 / (params.K_2T + t1))
        - params.k_d * t0
    )
    dt1 = (
        params.V_1T * (t0 / (params.K_1T + t0))
        - params.V_2T * (t1 / (params.K_2T + t1))
        - params.V_3T * (t1 / (params.K_3T + t1))
        + params.V_4T * (t2 / (params.K_4T + t2))
        - params.k_d * t1
    )
    dt2 = (
        params.V_3T * (t1 / (params.K_3T + t1))
        - params.V_4T * (t2 / (params.K_4T + t2))
        - params.k3 * p2 * t2
        + params.k4 * c_cyto
        - v_dt * (t2 / (params.K_dT + t2))
        - params.k_d * t2
    )

    dc_cyto = (
        params.k3 * p2 * t2
        - params.k4 * c_cyto
        - params.k1 * c_cyto
        + params.k2 * c_nuc
        - params.k_dC * c_cyto
    )
    dc_nuc = params.k1 * c_cyto - params.k2 * c_nuc - params.k_dN * c_nuc
    return [dm_p, dp0, dp1, dp2, dm_t, dt0, dt1, dt2, dc_cyto, dc_nuc]


def simulate_two_process(
    params: CircadianHomeostaticParameters,
    duration_h: float,
    light_schedule: Callable[[float], float],
    *,
    deprivation_windows: Sequence[tuple[float, float]] = (),
    y0: Sequence[float] | None = None,
    max_step_h: float | None = None,
) -> TwoProcessTrajectory:
    """Integrate the molecular PER/TIM circadian oscillator coupled to Process S hysteresis."""
    if not math.isfinite(duration_h) or duration_h <= 0.0:
        raise ValueError(f"duration_h must be finite and > 0, got {duration_h!r}")
    for start_h, end_h in deprivation_windows:
        if not (math.isfinite(start_h) and math.isfinite(end_h)) or end_h <= start_h:
            raise ValueError(f"Invalid deprivation window {(start_h, end_h)!r}")

    dt = params.dt_eval_h
    n_steps = round(duration_h / dt)
    t_eval = np.round(np.linspace(0.0, n_steps * dt, n_steps + 1), 6)
    init_y = list(DEFAULT_Y0 if y0 is None else y0)
    if len(init_y) != 10:
        raise ValueError(f"Expected 10 state variables in y0, got {len(init_y)}")

    step_cap = params.max_step_h if max_step_h is None else float(max_step_h)
    sol = solve_ivp(
        lambda t, state: _leloup_goldbeter_rhs(t, state, params, light_schedule),
        (0.0, float(t_eval[-1])),
        init_y,
        method=params.solver,
        t_eval=t_eval,
        rtol=params.rtol,
        atol=params.atol,
        max_step=step_cap,
    )
    if not sol.success:
        raise RuntimeError(f"Circadian ODE solver failed: {sol.message}")

    y_mat = np.asarray(sol.y, dtype=np.float64)
    p_total = y_mat[1] + y_mat[2] + y_mat[3] + y_mat[8] + y_mat[9]
    t_total = y_mat[5] + y_mat[6] + y_mat[7] + y_mat[8] + y_mat[9]
    c_n = y_mat[9]

    # Circadian wake drive opposes nuclear PER-TIM repression (peaks during subjective day)
    c_wake = np.clip(-(c_n - params.cn_mid) / params.cn_half, -1.2, 1.2)
    u_thr = params.u_mean + params.a_c * c_wake
    l_thr = params.l_mean + params.a_c * c_wake

    light_arr = np.asarray(
        [float(np.clip(float(light_schedule(float(t))), 0.0, 1.0)) for t in t_eval],
        dtype=np.float64,
    )
    dep_mask = np.zeros(t_eval.size, dtype=bool)
    for w_start, w_end in deprivation_windows:
        dep_mask |= (t_eval >= float(w_start)) & (t_eval < float(w_end))

    s_arr = np.zeros(t_eval.size, dtype=np.float64)
    rest_state = np.zeros(t_eval.size, dtype=np.int8)
    s_val = float(params.s_init)
    state_flag = 0
    decay_wake = math.exp(-dt / params.tau_i_h)
    decay_rest = math.exp(-dt / params.tau_d_h)

    for idx in range(t_eval.size):
        s_arr[idx] = s_val
        if dep_mask[idx]:
            state_flag = 0
        else:
            if state_flag == 0 and s_val >= u_thr[idx]:
                state_flag = 1
            elif state_flag == 1 and s_val <= l_thr[idx]:
                state_flag = 0
        rest_state[idx] = state_flag

        if idx < t_eval.size - 1:
            if state_flag == 0:
                s_val = params.s_max - (params.s_max - s_val) * decay_wake
            else:
                s_val = params.s_min + (s_val - params.s_min) * decay_rest

    return TwoProcessTrajectory(
        times_h=t_eval,
        light=light_arr,
        y=y_mat,
        p_total=p_total,
        t_total=t_total,
        c_n=c_n,
        c_wake=c_wake,
        u_threshold=u_thr,
        l_threshold=l_thr,
        s_homeostat=s_arr,
        modeled_rest_state=rest_state,
        deprivation_mask=dep_mask,
    )


def _ld12_12(t_h: float) -> float:
    return 1.0 if (t_h % 24.0) < 12.0 else 0.0


def _make_light_pulse(start_h: float, end_h: float) -> Callable[[float], float]:
    def _pulse(t_h: float) -> float:
        return 1.0 if (start_h <= t_h < end_h) else 0.0

    return _pulse


def verify_circadian_homeostatic_gates(
    params: CircadianHomeostaticParameters,
) -> dict[str, Any]:
    """Verify DD period, convergence, LD entrainment, light PRC, and deprivation rebound."""
    # Gate 1: Constant Darkness (DD) free-running period + step-size convergence
    dd_coarse = simulate_two_process(params, 240.0, lambda _t: 0.0, max_step_h=params.max_step_h)
    dd_fine = simulate_two_process(
        params,
        240.0,
        lambda _t: 0.0,
        max_step_h=min(params.max_step_h * 0.25, 0.025),
    )
    dd_peaks = detect_oscillation_peaks(dd_coarse.times_h, dd_coarse.p_total, min_time_h=48.0)
    dd_fine_peaks = detect_oscillation_peaks(dd_fine.times_h, dd_fine.p_total, min_time_h=48.0)
    dd_periods = np.diff(dd_peaks) if dd_peaks.size >= 2 else np.empty(0, dtype=np.float64)
    dd_fine_periods = (
        np.diff(dd_fine_peaks) if dd_fine_peaks.size >= 2 else np.empty(0, dtype=np.float64)
    )
    tau_dd = float(np.mean(dd_periods)) if dd_periods.size > 0 else float("nan")
    tau_dd_sd = float(np.std(dd_periods)) if dd_periods.size > 1 else float("nan")
    tau_dd_fine = float(np.mean(dd_fine_periods)) if dd_fine_periods.size > 0 else float("nan")
    conv_diff = (
        abs(tau_dd - tau_dd_fine)
        if math.isfinite(tau_dd) and math.isfinite(tau_dd_fine)
        else float("inf")
    )
    gate1_pass = bool(
        dd_periods.size >= 4 and 23.5 <= tau_dd <= 24.8 and tau_dd_sd < 0.05 and conv_diff < 0.05
    )

    # Gate 2: LD 12:12 entrainment over 14 days, checking steady-state window t >= 192 h (Days 8-13)
    ld_traj = simulate_two_process(params, 336.0, _ld12_12)
    ld_peaks = detect_oscillation_peaks(ld_traj.times_h, ld_traj.p_total, min_time_h=192.0)
    ld_periods = np.diff(ld_peaks) if ld_peaks.size >= 2 else np.empty(0, dtype=np.float64)
    ld_zts = np.mod(ld_peaks, 24.0) if ld_peaks.size > 0 else np.empty(0, dtype=np.float64)
    tau_ld = float(np.mean(ld_periods)) if ld_periods.size > 0 else float("nan")
    zt_sd = float(np.std(ld_zts)) if ld_zts.size > 1 else float("nan")
    zt_mean = float(np.mean(ld_zts)) if ld_zts.size > 0 else float("nan")
    gate2_pass = bool(ld_periods.size >= 4 and abs(tau_ld - 24.0) <= 0.10 and zt_sd < 0.10)

    # Gate 3: 2-hour light-pulse PRC across CT 0..21 after entrained LD release
    idx_release = int(np.argmin(np.abs(ld_traj.times_h - 240.0)))
    y_release = ld_traj.y[:, idx_release].tolist()
    ref_traj = simulate_two_process(params, 168.0, lambda _t: 0.0, y0=y_release)
    ref_peaks = detect_oscillation_peaks(ref_traj.times_h, ref_traj.p_total, min_time_h=96.0)
    t_ref_peak = float(ref_peaks[-1]) if ref_peaks.size > 0 else float("nan")
    ref_period = tau_dd if math.isfinite(tau_dd) else 24.1

    prc_rows: list[dict[str, Any]] = []
    if math.isfinite(t_ref_peak):
        for ct_h in range(0, 24, 3):
            p_start = 24.0 + ct_h * (ref_period / 24.0)
            p_end = p_start + 2.0
            pulsed = simulate_two_process(
                params,
                168.0,
                _make_light_pulse(p_start, p_end),
                y0=y_release,
            )
            p_peaks = detect_oscillation_peaks(pulsed.times_h, pulsed.p_total, min_time_h=96.0)
            if p_peaks.size == 0:
                shift_h = float("nan")
            else:
                shifts = [wrap_phase_hours(t_ref_peak - float(pk), ref_period) for pk in p_peaks]
                shift_h = min(shifts, key=abs)
            prc_rows.append(
                {
                    "ct_hours": ct_h,
                    "pulse_start_h": round(p_start, 4),
                    "pulse_end_h": round(p_end, 4),
                    "phase_shift_h": round(shift_h, 4) if math.isfinite(shift_h) else None,
                    "direction": (
                        "advance"
                        if (math.isfinite(shift_h) and shift_h > 0.15)
                        else (
                            "delay" if (math.isfinite(shift_h) and shift_h < -0.15) else "dead_zone"
                        )
                    ),
                }
            )

    day_shifts = [
        abs(float(r["phase_shift_h"]))
        for r in prc_rows
        if r["ct_hours"] in (3, 6, 9) and r["phase_shift_h"] is not None
    ]
    delay_shifts = [
        float(r["phase_shift_h"])
        for r in prc_rows
        if r["ct_hours"] in (12, 15, 18) and r["phase_shift_h"] is not None
    ]
    ct21 = next((r["phase_shift_h"] for r in prc_rows if r["ct_hours"] == 21), None)
    gate3_pass = bool(
        len(prc_rows) == 8
        and len(day_shifts) == 3
        and max(day_shifts) < 0.35
        and len(delay_shifts) == 3
        and min(delay_shifts) < -0.50
        and ct21 is not None
        and float(ct21) > 1.00
    )

    # Gate 4: 12 h Night-6 forced-wake deprivation + recovery rebound (Day 6 -> Day 9 washout)
    base_336 = ld_traj
    dep_336 = simulate_two_process(
        params,
        336.0,
        _ld12_12,
        deprivation_windows=((156.0, 168.0),),
    )
    t_arr = base_336.times_h
    dep_win_mask = (t_arr >= 156.0) & (t_arr <= 168.0)
    rec_mask = (t_arr >= 168.0) & (t_arr < 192.0)
    washout_mask = (t_arr >= 216.0) & (t_arr < 240.0)

    base_s_peak = float(np.max(base_336.s_homeostat[dep_win_mask]))
    dep_s_peak = float(np.max(dep_336.s_homeostat[dep_win_mask]))
    base_rec_rest = float(np.mean(base_336.modeled_rest_state[rec_mask]))
    dep_rec_rest = float(np.mean(dep_336.modeled_rest_state[rec_mask]))
    rec_rest_delta = dep_rec_rest - base_rec_rest
    washout_rest_delta = float(np.mean(dep_336.modeled_rest_state[washout_mask])) - float(
        np.mean(base_336.modeled_rest_state[washout_mask])
    )
    gate4_pass = bool(
        dep_s_peak > base_s_peak + 0.10 and rec_rest_delta > 0.08 and abs(washout_rest_delta) < 0.03
    )

    overall_passed = gate1_pass and gate2_pass and gate3_pass and gate4_pass
    return {
        "schema_version": "1.0",
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "model_level": params.model_level,
        "parameter_manifest_sha256": params.canonical_sha256(),
        "parameter_source": params.parameter_source,
        "ruo_notice": (
            "Research Use Only (RUO): Mathematical circadian-homeostatic model (L3). "
            "Quiescence/rest state is a model proxy and is not validated behavioral sleep."
        ),
        "overall_passed": overall_passed,
        "gates": {
            "dd_free_running_and_convergence": {
                "passed": gate1_pass,
                "tau_dd_coarse_h": round(tau_dd, 4) if math.isfinite(tau_dd) else None,
                "tau_dd_sd_h": round(tau_dd_sd, 5) if math.isfinite(tau_dd_sd) else None,
                "tau_dd_fine_h": round(tau_dd_fine, 4) if math.isfinite(tau_dd_fine) else None,
                "convergence_abs_diff_h": round(conv_diff, 5) if math.isfinite(conv_diff) else None,
                "criterion": "23.5 <= tau_dd <= 24.8 h, sd < 0.05 h, convergence_abs_diff < 0.05 h",
            },
            "ld12_12_entrainment": {
                "passed": gate2_pass,
                "tau_ld_h": round(tau_ld, 4) if math.isfinite(tau_ld) else None,
                "zt_peak_mean_h": round(zt_mean, 4) if math.isfinite(zt_mean) else None,
                "zt_peak_sd_h": round(zt_sd, 5) if math.isfinite(zt_sd) else None,
                "criterion": "|tau_ld - 24.0| <= 0.10 h and zt_peak_sd < 0.10 h",
            },
            "light_pulse_prc": {
                "passed": gate3_pass,
                "reference_peak_h": round(t_ref_peak, 4) if math.isfinite(t_ref_peak) else None,
                "max_abs_daytime_dead_zone_h": round(max(day_shifts), 4) if day_shifts else None,
                "max_early_night_delay_h": round(min(delay_shifts), 4) if delay_shifts else None,
                "late_night_ct21_advance_h": ct21,
                "curve": prc_rows,
                "criterion": (
                    "CT3-9 |shift| < 0.35 h; CT12-18 min shift < -0.50 h; CT21 shift > +1.00 h"
                ),
            },
            "homeostatic_deprivation_rebound": {
                "passed": gate4_pass,
                "baseline_s_peak": round(base_s_peak, 4),
                "deprivation_s_peak": round(dep_s_peak, 4),
                "baseline_24h_recovery_rest_fraction": round(base_rec_rest, 4),
                "deprivation_24h_recovery_rest_fraction": round(dep_rec_rest, 4),
                "recovery_rest_fraction_delta": round(rec_rest_delta, 4),
                "day9_washout_rest_fraction_delta": round(washout_rest_delta, 4),
                "criterion": (
                    "dep_s_peak > base + 0.10; recovery_delta > +0.08; |day9_washout| < 0.03"
                ),
            },
        },
    }


def _schedule_light_delay_8h(t_h: float) -> float:
    if t_h < 144.0:
        return _ld12_12(t_h)
    return 1.0 if ((t_h - 8.0) % 24.0) < 12.0 else 0.0


def _schedule_light_advance_6h(t_h: float) -> float:
    if t_h < 144.0:
        return _ld12_12(t_h)
    return 1.0 if ((t_h + 6.0) % 24.0) < 12.0 else 0.0


def _schedule_light_rotating_8h(t_h: float) -> float:
    if t_h < 144.0:
        return _ld12_12(t_h)
    if 144.0 <= t_h < 216.0 or 288.0 <= t_h < 360.0:
        return 1.0 if ((t_h - 8.0) % 24.0) < 12.0 else 0.0
    return _ld12_12(t_h)


def _target_zt_shift_for_arm(arm_id: str, t_h: float) -> float:
    if arm_id in ("ld12_12_control", "deprivation_12h_recovery") or t_h < 144.0:
        return 0.0
    if arm_id == "shift_delay_8h":
        return 8.0
    if arm_id == "shift_advance_6h":
        return -6.0
    if arm_id == "rotating_shift_8h":
        if 144.0 <= t_h < 216.0 or 288.0 <= t_h < 360.0:
            return 8.0
        return 0.0
    return 0.0


def run_shift_work_experiment(
    params: CircadianHomeostaticParameters | None = None,
    *,
    require_verified_gate: bool = True,
) -> tuple[dict[str, Any], dict[str, TwoProcessTrajectory]]:
    """Run L3 shift-work & forced-wake schedules ONLY after oscillator verification passes."""
    cfg = CircadianHomeostaticParameters() if params is None else params
    gate_report = verify_circadian_homeostatic_gates(cfg)
    if require_verified_gate and not gate_report["overall_passed"]:
        raise RuntimeError(
            "Refusing to simulate shift-work schedules before circadian-homeostatic "
            "verification gates pass"
        )

    zt_target = float(gate_report["gates"]["ld12_12_entrainment"]["zt_peak_mean_h"] or 21.4)
    duration_h = 384.0
    arm_specs: list[tuple[str, Callable[[float], float], tuple[tuple[float, float], ...]]] = [
        ("ld12_12_control", _ld12_12, ()),
        ("deprivation_12h_recovery", _ld12_12, ((156.0, 168.0),)),
        ("shift_delay_8h", _schedule_light_delay_8h, ()),
        ("shift_advance_6h", _schedule_light_advance_6h, ()),
        ("rotating_shift_8h", _schedule_light_rotating_8h, ()),
    ]

    trajectories: dict[str, TwoProcessTrajectory] = {}
    arms_summary: dict[str, Any] = {}
    for arm_id, light_fn, dep_windows in arm_specs:
        traj = simulate_two_process(cfg, duration_h, light_fn, deprivation_windows=dep_windows)
        trajectories[arm_id] = traj

        peaks = detect_oscillation_peaks(traj.times_h, traj.p_total, min_time_h=100.0)
        post_onset_errors: list[dict[str, float]] = []
        for pk in peaks:
            if pk < 144.0:
                continue
            target_mod = (zt_target + _target_zt_shift_for_arm(arm_id, float(pk))) % 24.0
            err_h = wrap_phase_hours(float(pk % 24.0) - target_mod, 24.0)
            post_onset_errors.append(
                {
                    "peak_time_h": round(float(pk), 3),
                    "day": round(float(pk) / 24.0, 2),
                    "phase_error_h": round(err_h, 3),
                }
            )

        abs_errors = [abs(e["phase_error_h"]) for e in post_onset_errors]
        max_abs_err = max(abs_errors) if abs_errors else 0.0

        # Stable re-entrainment: first peak where |phase_error| < 1.0 h AND stays < 1.0 h to day 16
        days_to_reentrain: float | None = None
        if abs_errors:
            for i in range(len(post_onset_errors)):
                if all(
                    abs(post_onset_errors[j]["phase_error_h"]) < 1.0
                    for j in range(i, len(post_onset_errors))
                ):
                    days_to_reentrain = round(
                        (post_onset_errors[i]["peak_time_h"] - 144.0) / 24.0, 3
                    )
                    break

        daily_rows: list[dict[str, float | int]] = []
        for day_idx in range(16):
            mask = (traj.times_h >= day_idx * 24.0) & (traj.times_h < (day_idx + 1) * 24.0)
            daily_rows.append(
                {
                    "day": day_idx,
                    "modeled_rest_fraction": round(
                        float(np.mean(traj.modeled_rest_state[mask])), 4
                    ),
                    "mean_s_homeostat": round(float(np.mean(traj.s_homeostat[mask])), 4),
                    "max_s_homeostat": round(float(np.max(traj.s_homeostat[mask])), 4),
                    "mean_c_wake": round(float(np.mean(traj.c_wake[mask])), 4),
                }
            )

        post_mask = traj.times_h >= 144.0
        arms_summary[arm_id] = {
            "arm_id": arm_id,
            "duration_h": duration_h,
            "s_peak_overall": round(float(np.max(traj.s_homeostat[post_mask])), 4),
            "s_mean_post_onset": round(float(np.mean(traj.s_homeostat[post_mask])), 4),
            "modeled_rest_fraction_post_onset": round(
                float(np.mean(traj.modeled_rest_state[post_mask])), 4
            ),
            "max_abs_phase_error_h": round(max_abs_err, 3),
            "days_to_reentrain": days_to_reentrain,
            "post_onset_phase_errors": post_onset_errors,
            "daily_profile": daily_rows,
        }

    # Explicit quasi-steady-state L3 -> L1 probe table (timescale-separated)
    ctrl_traj = trajectories["ld12_12_control"]
    dep_traj = trajectories["deprivation_12h_recovery"]
    idx_zt6 = int(np.argmin(np.abs(ctrl_traj.times_h - 150.0)))  # ZT 6 midday on day 6
    idx_zt10 = int(np.argmin(np.abs(ctrl_traj.times_h - 154.0)))  # ZT 10 evening wake-drive window
    idx_dep_end = int(np.argmin(np.abs(dep_traj.times_h - 168.0)))  # End of 12 h deprivation
    coupling_snapshots = [
        {
            "state_label": "daytime_light_low_sleep_pressure",
            "l3_time_h": round(float(ctrl_traj.times_h[idx_zt6]), 2),
            "l3_light": round(float(ctrl_traj.light[idx_zt6]), 2),
            "l3_c_wake": round(float(ctrl_traj.c_wake[idx_zt6]), 3),
            "l3_s_homeostat": round(float(ctrl_traj.s_homeostat[idx_zt6]), 3),
            "l1_condition_mapping": (
                "light_day_baseline (MeTu2a 30 Hz + aMe12 40 Hz, ER5 gain 1.0x)"
            ),
        },
        {
            "state_label": "evening_clock_wake_drive_window",
            "l3_time_h": round(float(ctrl_traj.times_h[idx_zt10]), 2),
            "l3_light": round(float(ctrl_traj.light[idx_zt10]), 2),
            "l3_c_wake": round(float(ctrl_traj.c_wake[idx_zt10]), 3),
            "l3_s_homeostat": round(float(ctrl_traj.s_homeostat[idx_zt10]), 3),
            "l1_condition_mapping": "light_plus_clock_dn1p_drive (+ DN1p 40 Hz probe)",
        },
        {
            "state_label": "post_deprivation_high_homeostatic_debt",
            "l3_time_h": round(float(dep_traj.times_h[idx_dep_end]), 2),
            "l3_light": round(float(dep_traj.light[idx_dep_end]), 2),
            "l3_c_wake": round(float(dep_traj.c_wake[idx_dep_end]), 3),
            "l3_s_homeostat": round(float(dep_traj.s_homeostat[idx_dep_end]), 3),
            "l1_condition_mapping": (
                "light_plus_er5_high_homeostat_gain & "
                "shift_light_misaligned_clock_debt (ER5 gain 1.5x)"
            ),
        },
    ]

    summary = {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "timescale_coupling_note": (
            f"L3 evaluates over hours (dt_eval={cfg.dt_eval_h} h = "
            f"{cfg.dt_eval_h * cfg.seconds_per_hour:.0f} s); L1 whole-CNS LIF probes "
            "(0.8 s trials, dt=0.1 ms) sample quasi-steady-state parameter snapshots."
        ),
        "gate_overall_passed": bool(gate_report["overall_passed"]),
        "arms": arms_summary,
        "l3_to_l1_coupling_snapshots": coupling_snapshots,
    }
    return summary, trajectories
