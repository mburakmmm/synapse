"""L2 Drosophila mushroom-body dopamine-gated synaptic plasticity and conditioning paradigms."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

ARM_IDS: tuple[str, ...] = (
    "paired_conditioning",
    "spontaneous_recovery_only",
    "yoked_unpaired",
    "sham_no_stimulus",
    "dan_blocked",
)

STATE_NAMES: tuple[str, ...] = (
    "e_cs_plus",
    "e_cs_minus",
    "d_pam",
    "d_ppl1",
    "w_avoid_cs_plus",
    "w_avoid_cs_minus",
    "w_appr_cs_plus",
    "w_appr_cs_minus",
)

# Phase schedule constants (seconds):
# Phase 0 Baseline [0, 10) -> Phase 1 Acquisition [10, 145) ->
# Phase 2 Extinction [145, 235) -> Phase 3 Reinstatement / Retention [235, 310]
PHASE_EVAL_TIMES_S: dict[str, float] = {
    "naive": 10.0,
    "acquisition": 145.0,
    "extinction": 235.0,
    "reinstatement": 310.0,
}
TOTAL_PARADIGM_DURATION_S: float = 310.0


class MBPlasticityParameters(BaseModel):
    """Immutable parameter set for two-compartment mushroom-body three-factor plasticity.

    Models CS+ / CS- Kenyon cell eligibility traces (``tau_e_s``), compartmental dopamine
    transients (``d_pam`` for reward PAM inputs; ``d_ppl1`` for reward-omission PPL1 inputs),
    parallel opposing synaptic weights (``w_avoid`` onto PAM-innervated glutamatergic
    avoidance MBON02/04; ``w_appr`` onto PPL1-innervated cholinergic approach MBON12/14/18),
    and feedforward cross-compartment inhibition ``g_cross`` matching MaleCNS ``MBON02 -> MBON14``.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "mb_dopamine_plasticity_v1"
    model_revision: str = "1.0"
    model_level: Literal["L2"] = "L2"
    solver: Literal["rk4"] = "rk4"

    dt_s: float = 0.05
    tau_e_s: float = 4.0
    tau_d_s: float = 1.5
    eta_ltd_pam: float = 0.09
    eta_ltd_ppl1: float = 0.10
    eta_pot_reinst: float = 0.08
    omission_gain: float = 1.2
    tau_rec_avoid_s: float = 1500.0
    tau_rec_appr_s: float = 150.0
    w_init: float = 1.0
    w_min: float = 0.15
    w_max: float = 1.0
    r_base_hz: float = 40.0
    g_cross: float = 0.25
    eps_hz: float = 1e-6

    parameter_source: str = (
        "Aso et al. (2014 eLife 10.7554/eLife.04580); "
        "Owald et al. (2015 Neuron 10.1016/j.neuron.2015.03.025); "
        "Hige et al. (2015 Neuron 10.1016/j.neuron.2015.11.003); "
        "Cohn et al. (2015 Cell 10.1016/j.cell.2015.11.019); "
        "Felsenberg et al. (2017 Nature; 2018 Cell 10.1016/j.cell.2018.08.021); "
        "Handler et al. (2019 Cell 10.1016/j.cell.2019.05.040); "
        "Gkanias et al. (2022 eLife 10.7554/eLife.75611)"
    )

    @model_validator(mode="after")
    def _validate_physics(self) -> MBPlasticityParameters:
        strictly_positive = (
            "dt_s",
            "tau_e_s",
            "tau_d_s",
            "tau_rec_avoid_s",
            "tau_rec_appr_s",
            "r_base_hz",
            "eps_hz",
        )
        non_negative = (
            "eta_ltd_pam",
            "eta_ltd_ppl1",
            "eta_pot_reinst",
            "omission_gain",
            "g_cross",
        )
        for name in strictly_positive:
            val = getattr(self, name)
            if not math.isfinite(val) or val <= 0.0:
                raise ValueError(f"{name} must be finite and > 0, got {val!r}")
        for name in non_negative:
            val = getattr(self, name)
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{name} must be finite and >= 0, got {val!r}")
        for name in ("w_min", "w_init", "w_max"):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        if not (0.0 <= self.w_min < self.w_init <= self.w_max):
            raise ValueError("Weights must satisfy 0.0 <= w_min < w_init <= w_max")
        return self

    def canonical_sha256(self) -> str:
        """Return canonical SHA-256 hash of the frozen L2 parameter manifest."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PlasticityTrajectory:
    """Time-resolved L2 plasticity state, dopamine transients, MBON readouts, and PI proxy."""

    arm_id: str
    times_s: np.ndarray
    r_kc_cs_plus: np.ndarray
    r_kc_cs_minus: np.ndarray
    u_reward: np.ndarray
    e_cs_plus: np.ndarray
    e_cs_minus: np.ndarray
    d_pam: np.ndarray
    d_ppl1: np.ndarray
    w_avoid_cs_plus: np.ndarray
    w_avoid_cs_minus: np.ndarray
    w_appr_cs_plus: np.ndarray
    w_appr_cs_minus: np.ndarray
    pi_proxy: np.ndarray
    v_cs_plus: np.ndarray
    v_cs_minus: np.ndarray


def compute_preference_metrics(
    w_avoid_plus: float,
    w_avoid_minus: float,
    w_appr_plus: float,
    w_appr_minus: float,
    params: MBPlasticityParameters,
) -> dict[str, float]:
    """Compute opposing MBON firing proxies, odor valences, and differential Preference Index."""
    r_av_plus = max(0.0, params.r_base_hz * w_avoid_plus)
    r_av_minus = max(0.0, params.r_base_hz * w_avoid_minus)
    r_ap_plus = max(0.0, params.r_base_hz * w_appr_plus - params.g_cross * r_av_plus)
    r_ap_minus = max(0.0, params.r_base_hz * w_appr_minus - params.g_cross * r_av_minus)

    v_plus = (r_ap_plus - r_av_plus) / (r_ap_plus + r_av_plus + params.eps_hz)
    v_minus = (r_ap_minus - r_av_minus) / (r_ap_minus + r_av_minus + params.eps_hz)
    pi = 0.5 * (v_plus - v_minus)
    return {
        "r_avoid_cs_plus_hz": r_av_plus,
        "r_avoid_cs_minus_hz": r_av_minus,
        "r_appr_cs_plus_hz": r_ap_plus,
        "r_appr_cs_minus_hz": r_ap_minus,
        "v_cs_plus": v_plus,
        "v_cs_minus": v_minus,
        "preference_index_proxy": pi,
    }


def _in_windows(t_s: float, windows: tuple[tuple[float, float], ...]) -> float:
    return 1.0 if any(start <= t_s < end for start, end in windows) else 0.0


def _arm_inputs(
    arm_id: str,
    t_s: float,
) -> tuple[float, float, float]:
    """Return normalized ``(r_kc_cs_plus, r_kc_cs_minus, u_reward)`` at time ``t_s``."""
    ext_plus_windows = (
        (150.0, 160.0),
        (170.0, 180.0),
        (190.0, 200.0),
        (210.0, 220.0),
    )
    if arm_id == "sham_no_stimulus":
        return 0.0, 0.0, 0.0
    if arm_id == "yoked_unpaired":
        # Exact equal exposure totals (30 s CS-, 30 s CS+ acq + 40 s CS+ ext, 30 s PAM)
        # separated by 28.0 s washout (28 / tau_e = 7.0 time constants) before PAM arrives.
        r_minus = _in_windows(t_s, ((10.0, 20.0), (21.0, 31.0), (32.0, 42.0)))
        r_plus = _in_windows(
            t_s,
            ((45.0, 55.0), (56.0, 66.0), (67.0, 77.0), *ext_plus_windows),
        )
        u_reward = _in_windows(t_s, ((105.0, 115.0), (116.0, 126.0), (127.0, 137.0)))
        return r_plus, r_minus, u_reward
    if arm_id in ("paired_conditioning", "spontaneous_recovery_only", "dan_blocked"):
        r_plus = _in_windows(
            t_s,
            ((10.0, 20.0), (21.0, 31.0), (32.0, 42.0), *ext_plus_windows),
        )
        r_minus = _in_windows(t_s, ((70.0, 80.0), (81.0, 91.0), (92.0, 102.0)))
        if arm_id == "dan_blocked":
            u_reward = 0.0
        elif arm_id == "paired_conditioning":
            u_reward = _in_windows(
                t_s,
                (
                    (10.0, 20.0),
                    (21.0, 31.0),
                    (32.0, 42.0),
                    (265.0, 275.0),
                    (280.0, 290.0),
                ),
            )
        else:
            u_reward = _in_windows(t_s, ((10.0, 20.0), (21.0, 31.0), (32.0, 42.0)))
        return r_plus, r_minus, u_reward
    raise ValueError(f"Unknown conditioning arm_id: {arm_id!r}")


def simulate_conditioning_schedule(
    params: MBPlasticityParameters | None = None,
    *,
    arm_id: str = "paired_conditioning",
    extinction_omission_enabled: bool = True,
    dt_override_s: float | None = None,
) -> PlasticityTrajectory:
    """Integrate the L2 three-factor MB plasticity ODEs with 4th-order Runge-Kutta (RK4)."""
    cfg = MBPlasticityParameters() if params is None else params
    dt = cfg.dt_s if dt_override_s is None else float(dt_override_s)
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError(f"dt_override_s must be finite and > 0, got {dt!r}")

    n_steps = round(TOTAL_PARADIGM_DURATION_S / dt)
    times = np.linspace(0.0, TOTAL_PARADIGM_DURATION_S, n_steps + 1, dtype=np.float64)

    states = np.zeros((8, n_steps + 1), dtype=np.float64)
    r_plus_arr = np.zeros(n_steps + 1, dtype=np.float64)
    r_minus_arr = np.zeros(n_steps + 1, dtype=np.float64)
    u_reward_arr = np.zeros(n_steps + 1, dtype=np.float64)
    pi_arr = np.zeros(n_steps + 1, dtype=np.float64)
    v_plus_arr = np.zeros(n_steps + 1, dtype=np.float64)
    v_minus_arr = np.zeros(n_steps + 1, dtype=np.float64)

    y = np.array(
        [0.0, 0.0, 0.0, 0.0, cfg.w_init, cfg.w_init, cfg.w_init, cfg.w_init],
        dtype=np.float64,
    )

    def rhs(t_val: float, state: np.ndarray) -> np.ndarray:
        ep, em, dp, d1, wav, wam, wap, wmp = state
        rp, rm, ur = _arm_inputs(arm_id, t_val)
        if extinction_omission_enabled and ur == 0.0:
            pred_err_plus = max(0.0, cfg.w_init - wav) * rp
            pred_err_minus = max(0.0, cfg.w_init - wam) * rm
            u_om = cfg.omission_gain * (pred_err_plus + pred_err_minus)
        else:
            u_om = 0.0

        d_ep = (-ep + rp) / cfg.tau_e_s
        d_em = (-em + rm) / cfg.tau_e_s
        d_dp = (-dp + ur) / cfg.tau_d_s
        d_d1 = (-d1 + u_om) / cfg.tau_d_s
        d_wav = (
            -cfg.eta_ltd_pam * ep * dp * (wav - cfg.w_min)
            + (cfg.w_init - wav) / cfg.tau_rec_avoid_s
        )
        d_wam = (
            -cfg.eta_ltd_pam * em * dp * (wam - cfg.w_min)
            + (cfg.w_init - wam) / cfg.tau_rec_avoid_s
        )
        d_wap = (
            -cfg.eta_ltd_ppl1 * ep * d1 * (wap - cfg.w_min)
            + cfg.eta_pot_reinst * dp * (cfg.w_init - wap)
            + (cfg.w_init - wap) / cfg.tau_rec_appr_s
        )
        d_wmp = (
            -cfg.eta_ltd_ppl1 * em * d1 * (wmp - cfg.w_min)
            + cfg.eta_pot_reinst * dp * (cfg.w_init - wmp)
            + (cfg.w_init - wmp) / cfg.tau_rec_appr_s
        )
        return np.array(
            [d_ep, d_em, d_dp, d_d1, d_wav, d_wam, d_wap, d_wmp],
            dtype=np.float64,
        )

    for idx in range(n_steps + 1):
        t_cur = float(times[idx])
        states[:, idx] = y
        rp, rm, ur = _arm_inputs(arm_id, t_cur)
        r_plus_arr[idx] = rp
        r_minus_arr[idx] = rm
        u_reward_arr[idx] = ur

        metrics = compute_preference_metrics(
            float(y[4]),
            float(y[5]),
            float(y[6]),
            float(y[7]),
            cfg,
        )
        pi_arr[idx] = metrics["preference_index_proxy"]
        v_plus_arr[idx] = metrics["v_cs_plus"]
        v_minus_arr[idx] = metrics["v_cs_minus"]

        if idx < n_steps:
            k1 = rhs(t_cur, y)
            k2 = rhs(t_cur + 0.5 * dt, y + 0.5 * dt * k1)
            k3 = rhs(t_cur + 0.5 * dt, y + 0.5 * dt * k2)
            k4 = rhs(t_cur + dt, y + dt * k3)
            y = y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            y[4:] = np.clip(y[4:], cfg.w_min, cfg.w_max)

    return PlasticityTrajectory(
        arm_id=arm_id,
        times_s=times,
        r_kc_cs_plus=r_plus_arr,
        r_kc_cs_minus=r_minus_arr,
        u_reward=u_reward_arr,
        e_cs_plus=states[0],
        e_cs_minus=states[1],
        d_pam=states[2],
        d_ppl1=states[3],
        w_avoid_cs_plus=states[4],
        w_avoid_cs_minus=states[5],
        w_appr_cs_plus=states[6],
        w_appr_cs_minus=states[7],
        pi_proxy=pi_arr,
        v_cs_plus=v_plus_arr,
        v_cs_minus=v_minus_arr,
    )


def _snapshot_at_time(traj: PlasticityTrajectory, t_s: float) -> dict[str, float]:
    idx = int(np.argmin(np.abs(traj.times_s - t_s)))
    return {
        "time_s": round(float(traj.times_s[idx]), 3),
        "pi_proxy": round(float(traj.pi_proxy[idx]), 6),
        "v_cs_plus": round(float(traj.v_cs_plus[idx]), 6),
        "v_cs_minus": round(float(traj.v_cs_minus[idx]), 6),
        "w_avoid_cs_plus": round(float(traj.w_avoid_cs_plus[idx]), 6),
        "w_avoid_cs_minus": round(float(traj.w_avoid_cs_minus[idx]), 7),
        "w_appr_cs_plus": round(float(traj.w_appr_cs_plus[idx]), 6),
        "w_appr_cs_minus": round(float(traj.w_appr_cs_minus[idx]), 7),
    }


def verify_plasticity_paradigm_gates(
    params: MBPlasticityParameters | None = None,
) -> dict[str, Any]:
    """Evaluate all 5 mandatory L2 verification gates prior to experimental runs."""
    cfg = MBPlasticityParameters() if params is None else params

    paired = simulate_conditioning_schedule(cfg, arm_id="paired_conditioning")
    paired_fine = simulate_conditioning_schedule(
        cfg,
        arm_id="paired_conditioning",
        dt_override_s=cfg.dt_s * 0.5,
    )
    sham = simulate_conditioning_schedule(cfg, arm_id="sham_no_stimulus")
    yoked = simulate_conditioning_schedule(cfg, arm_id="yoked_unpaired")
    dan_blocked = simulate_conditioning_schedule(cfg, arm_id="dan_blocked")

    # Gate 1: RK4 step-size convergence (dt vs dt/2) and strict [w_min, w_max] invariance
    w_coarse = np.vstack(
        [
            paired.w_avoid_cs_plus,
            paired.w_avoid_cs_minus,
            paired.w_appr_cs_plus,
            paired.w_appr_cs_minus,
        ]
    )
    w_fine_sub = np.vstack(
        [
            paired_fine.w_avoid_cs_plus[::2],
            paired_fine.w_avoid_cs_minus[::2],
            paired_fine.w_appr_cs_plus[::2],
            paired_fine.w_appr_cs_minus[::2],
        ]
    )
    max_w_diff = float(np.max(np.abs(w_coarse - w_fine_sub)))
    max_pi_diff = float(np.max(np.abs(paired.pi_proxy - paired_fine.pi_proxy[::2])))
    weights_in_bounds = bool(
        np.all(w_coarse >= cfg.w_min - 1e-12)
        and np.all(w_coarse <= cfg.w_max + 1e-12)
        and np.all(np.isfinite(w_coarse))
        and np.all(np.isfinite(paired.pi_proxy))
    )
    gate1_pass = bool(weights_in_bounds and max_w_diff < 1e-3 and max_pi_diff < 1e-3)

    snap_naive = _snapshot_at_time(paired, PHASE_EVAL_TIMES_S["naive"])
    snap_acq = _snapshot_at_time(paired, PHASE_EVAL_TIMES_S["acquisition"])
    snap_ext = _snapshot_at_time(paired, PHASE_EVAL_TIMES_S["extinction"])
    snap_reinst = _snapshot_at_time(paired, PHASE_EVAL_TIMES_S["reinstatement"])

    # Gate 2: CS+ vs CS- acquisition specificity
    pi_acq = snap_acq["pi_proxy"]
    w_av_plus_acq = snap_acq["w_avoid_cs_plus"]
    w_av_minus_acq_err = abs(snap_acq["w_avoid_cs_minus"] - cfg.w_init)
    v_minus_acq_err = abs(snap_acq["v_cs_minus"] - snap_naive["v_cs_minus"])
    gate2_pass = bool(
        pi_acq >= 0.30
        and w_av_plus_acq <= 0.55
        and w_av_minus_acq_err < 1e-6
        and v_minus_acq_err < 1e-4
    )

    # Gate 3: Parallel opposing memory extinction preserving the original reward trace
    pi_ext = snap_ext["pi_proxy"]
    ext_drop = pi_acq - pi_ext
    w_ap_plus_ext = snap_ext["w_appr_cs_plus"]
    w_av_plus_ext = snap_ext["w_avoid_cs_plus"]
    gate3_pass = bool(
        pi_ext <= 0.15 and ext_drop >= 0.25 and w_ap_plus_ext <= 0.55 and w_av_plus_ext <= 0.65
    )

    # Gate 4: Reinstatement recovery without corrupting CS-
    pi_reinst = snap_reinst["pi_proxy"]
    reinst_gain = pi_reinst - pi_ext
    w_av_minus_reinst_err = abs(snap_reinst["w_avoid_cs_minus"] - cfg.w_init)
    gate4_pass = bool(reinst_gain >= 0.15 and pi_reinst >= 0.25 and w_av_minus_reinst_err < 1e-6)

    # Gate 5: Nullity of sham, yoked_unpaired, and dan_blocked negative controls
    sham_max_pi = float(np.max(np.abs(sham.pi_proxy)))
    sham_max_w_dev = float(
        max(
            np.max(np.abs(sham.w_avoid_cs_plus - cfg.w_init)),
            np.max(np.abs(sham.w_avoid_cs_minus - cfg.w_init)),
            np.max(np.abs(sham.w_appr_cs_plus - cfg.w_init)),
            np.max(np.abs(sham.w_appr_cs_minus - cfg.w_init)),
        )
    )
    yoked_acq_pi = float(_snapshot_at_time(yoked, PHASE_EVAL_TIMES_S["acquisition"])["pi_proxy"])
    dan_max_pi = float(np.max(np.abs(dan_blocked.pi_proxy)))
    gate5_pass = bool(
        sham_max_pi < 1e-9
        and sham_max_w_dev == 0.0
        and abs(yoked_acq_pi) < 0.05
        and dan_max_pi < 1e-9
    )

    overall_passed = gate1_pass and gate2_pass and gate3_pass and gate4_pass and gate5_pass
    return {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "parameter_source": cfg.parameter_source,
        "ruo_notice": (
            "Research Use Only (RUO): L2 three-factor mushroom-body plasticity proxy. "
            "Preference Index (PI) is a Drosophila cue-valence proxy, NOT clinical dependence."
        ),
        "overall_passed": overall_passed,
        "gates": {
            "numerical_convergence_and_bounds": {
                "passed": gate1_pass,
                "dt_coarse_s": cfg.dt_s,
                "dt_fine_s": cfg.dt_s * 0.5,
                "weights_within_bounds": weights_in_bounds,
                "max_abs_weight_diff": round(max_w_diff, 8),
                "max_abs_pi_diff": round(max_pi_diff, 8),
                "criterion": (
                    "All weights in [w_min, w_max], max |dW| < 1e-3, max |dPI| < 1e-3 for dt/2"
                ),
            },
            "acquisition_specificity": {
                "passed": gate2_pass,
                "pi_acq": pi_acq,
                "w_avoid_cs_plus_acq": w_av_plus_acq,
                "w_avoid_cs_minus_abs_err": float(f"{w_av_minus_acq_err:.3e}"),
                "v_cs_minus_abs_err": float(f"{v_minus_acq_err:.3e}"),
                "criterion": (
                    "PI_acq >= 0.30, w_avoid(CS+) <= 0.55, |w_avoid(CS-) - 1.0| < 1e-6, "
                    "|V(CS-) - V_naive| < 1e-4"
                ),
            },
            "parallel_memory_extinction": {
                "passed": gate3_pass,
                "pi_ext": pi_ext,
                "pi_drop_acq_to_ext": round(ext_drop, 6),
                "w_appr_cs_plus_ext": w_ap_plus_ext,
                "w_avoid_cs_plus_ext": w_av_plus_ext,
                "criterion": (
                    "PI_ext <= 0.15, PI_acq - PI_ext >= 0.25, "
                    "w_appr(CS+) <= 0.55, original trace w_avoid(CS+) <= 0.65"
                ),
            },
            "reinstatement_recovery": {
                "passed": gate4_pass,
                "pi_reinst": pi_reinst,
                "pi_gain_ext_to_reinst": round(reinst_gain, 6),
                "w_appr_cs_plus_reinst": snap_reinst["w_appr_cs_plus"],
                "w_avoid_cs_minus_abs_err": float(f"{w_av_minus_reinst_err:.3e}"),
                "criterion": (
                    "PI_reinst - PI_ext >= 0.15, PI_reinst >= 0.25, |w_avoid(CS-) - 1.0| < 1e-6"
                ),
            },
            "negative_controls_null": {
                "passed": gate5_pass,
                "sham_max_abs_pi": sham_max_pi,
                "sham_max_weight_dev": sham_max_w_dev,
                "yoked_unpaired_acq_pi": yoked_acq_pi,
                "dan_blocked_max_abs_pi": dan_max_pi,
                "criterion": (
                    "sham max|PI| < 1e-9 & 0 weight shift; |yoked_acq PI| < 0.05; "
                    "dan_blocked max|PI| < 1e-9"
                ),
            },
        },
    }


def run_conditioning_paradigm(
    params: MBPlasticityParameters | None = None,
    *,
    require_verified_gate: bool = True,
) -> tuple[dict[str, Any], dict[str, PlasticityTrajectory]]:
    """Run all 5 L2 conditioning & control arms strictly after passing verification gates."""
    cfg = MBPlasticityParameters() if params is None else params
    gate_report = verify_plasticity_paradigm_gates(cfg)
    if require_verified_gate and not gate_report["overall_passed"]:
        raise RuntimeError(
            "Refusing to run conditioning paradigm before L2 plasticity verification gates pass"
        )

    trajectories: dict[str, PlasticityTrajectory] = {}
    arms_summary: dict[str, Any] = {}
    for arm_id in ARM_IDS:
        traj = simulate_conditioning_schedule(cfg, arm_id=arm_id)
        trajectories[arm_id] = traj
        snaps = {
            phase: _snapshot_at_time(traj, t_val) for phase, t_val in PHASE_EVAL_TIMES_S.items()
        }
        arms_summary[arm_id] = {
            "arm_id": arm_id,
            "duration_s": TOTAL_PARADIGM_DURATION_S,
            "phase_snapshots": snaps,
            "max_abs_pi_proxy": round(float(np.max(np.abs(traj.pi_proxy))), 6),
        }

    paired_snaps = arms_summary["paired_conditioning"]["phase_snapshots"]
    yoked_acq = arms_summary["yoked_unpaired"]["phase_snapshots"]["acquisition"]
    l2_to_l1_snapshots = [
        {
            "state_label": "naive_baseline",
            "l2_time_s": PHASE_EVAL_TIMES_S["naive"],
            "w_avoid_cs_plus": paired_snaps["naive"]["w_avoid_cs_plus"],
            "w_appr_cs_plus": paired_snaps["naive"]["w_appr_cs_plus"],
            "l2_pi_proxy": paired_snaps["naive"]["pi_proxy"],
            "l1_condition_mapping": "cs_plus_naive_baseline (1.000x KC->MBON weights)",
        },
        {
            "state_label": "post_acquisition",
            "l2_time_s": PHASE_EVAL_TIMES_S["acquisition"],
            "w_avoid_cs_plus": paired_snaps["acquisition"]["w_avoid_cs_plus"],
            "w_appr_cs_plus": paired_snaps["acquisition"]["w_appr_cs_plus"],
            "l2_pi_proxy": paired_snaps["acquisition"]["pi_proxy"],
            "l1_condition_mapping": (
                "cs_plus_post_acquisition (CS+ KCs -> MBON_avoid factor = "
                f"{paired_snaps['acquisition']['w_avoid_cs_plus']:.6f})"
            ),
        },
        {
            "state_label": "post_extinction",
            "l2_time_s": PHASE_EVAL_TIMES_S["extinction"],
            "w_avoid_cs_plus": paired_snaps["extinction"]["w_avoid_cs_plus"],
            "w_appr_cs_plus": paired_snaps["extinction"]["w_appr_cs_plus"],
            "l2_pi_proxy": paired_snaps["extinction"]["pi_proxy"],
            "l1_condition_mapping": (
                "cs_plus_post_extinction (MBON_avoid = "
                f"{paired_snaps['extinction']['w_avoid_cs_plus']:.6f}, "
                f"MBON_approach = {paired_snaps['extinction']['w_appr_cs_plus']:.6f})"
            ),
        },
        {
            "state_label": "post_reinstatement",
            "l2_time_s": PHASE_EVAL_TIMES_S["reinstatement"],
            "w_avoid_cs_plus": paired_snaps["reinstatement"]["w_avoid_cs_plus"],
            "w_appr_cs_plus": paired_snaps["reinstatement"]["w_appr_cs_plus"],
            "l2_pi_proxy": paired_snaps["reinstatement"]["pi_proxy"],
            "l1_condition_mapping": (
                "cs_plus_post_reinstatement (MBON_avoid = "
                f"{paired_snaps['reinstatement']['w_avoid_cs_plus']:.6f}, "
                f"MBON_approach = {paired_snaps['reinstatement']['w_appr_cs_plus']:.6f})"
            ),
        },
        {
            "state_label": "yoked_unpaired_control",
            "l2_time_s": PHASE_EVAL_TIMES_S["acquisition"],
            "w_avoid_cs_plus": yoked_acq["w_avoid_cs_plus"],
            "w_appr_cs_plus": yoked_acq["w_appr_cs_plus"],
            "l2_pi_proxy": yoked_acq["pi_proxy"],
            "l1_condition_mapping": "cs_plus_yoked_matched_ctrl (non-contingent control)",
        },
    ]

    summary = {
        "schema_version": "1.0",
        "model_id": cfg.model_id,
        "model_revision": cfg.model_revision,
        "model_level": cfg.model_level,
        "parameter_manifest_sha256": cfg.canonical_sha256(),
        "timescale_coupling_note": (
            f"L2 plasticity evolves across a {TOTAL_PARADIGM_DURATION_S:.0f} s conditioning trial "
            f"(dt={cfg.dt_s} s, tau_e={cfg.tau_e_s} s, tau_d={cfg.tau_d_s} s); L1 whole-CNS "
            "malecns_v1_0 LIF runs (0.6 s trials, dt=0.1 ms) sample frozen L2 weight snapshots."
        ),
        "gate_overall_passed": bool(gate_report["overall_passed"]),
        "arms": arms_summary,
        "l2_to_l1_weight_snapshots": l2_to_l1_snapshots,
    }
    return summary, trajectories


__all__ = [
    "ARM_IDS",
    "PHASE_EVAL_TIMES_S",
    "STATE_NAMES",
    "TOTAL_PARADIGM_DURATION_S",
    "MBPlasticityParameters",
    "PlasticityTrajectory",
    "compute_preference_metrics",
    "run_conditioning_paradigm",
    "simulate_conditioning_schedule",
    "verify_plasticity_paradigm_gates",
]
