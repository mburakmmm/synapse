# ADR-0007: Phase 5B Sleep Module — Two-Layer L3 Circadian-Homeostatic & L1 `malecns_v1_0` Coupling

- **Status:** Accepted (Phase 5B L3 Gates Verified + L1 Exploratory Pilot Architecture; Confirmatory Freeze Pending Human Approval)
- **Date:** 2026-11-23
- **Owners:** SYNAPSE Maintainers

## Context

`AGENTS.md` §7.1, §10, and §15 mandate that the **Sleep** module (`sleep`) must:
1. Explicitly add and verify **L3 circadian and homeostatic dynamics** (free-running period, numerical solver convergence, light entrainment, phase response curve, and homeostatic recovery) **before** simulating shift-work-like light schedules.
2. Never conflate modeled quiescence/rest states or firing-rate changes with validated biological sleep or human clinical sleep disorders.
3. Pair L1 whole-CNS connectome perturbations on `malecns_v1_0` (`211,577` bodies, `26,028,386` edges; single male specimen never pooled with female FlyWire) with structurally matched negative controls and explicit limitations.

## Decision

1. **Dual-Scale L3 + L1 Architecture with Explicit Timescale Separation (`packages/synapse_core/circadian.py` + `Brian2CPUBackend`):**
   - **L3 ODE + Two-Process Kernel (`leloup_goldbeter_1998_two_process_v1`):** Integrates the 10-variable *Drosophila* `PER/TIM` molecular oscillator using exact `BIOMD0000000021` parameters (`Leloup & Goldbeter, 1998`) coupled to normalized Process `S` hysteresis (`tau_i = 8.76 h`, `tau_d = 9.51 h`, `Abhilash & Shafer, 2024`; `Daan et al., 1984`). Time steps evolve on hour timescales (`dt_eval_h = 0.05 h = 180 s`).
   - **Pre-Shift-Work Gate Enforcement:** `run_shift_work_experiment(..., require_verified_gate=True)` calls `verify_circadian_homeostatic_gates` first and raises `RuntimeError` if any of the 4 quantitative gates fail (`DD period`, `LD 12:12 entrainment`, `2 h light-pulse PRC`, or `12 h forced-wake rebound`).
   - **Quasi-Steady-State L3 -> L1 Mapping:** Rather than fabricating unverified millisecond-to-24-hour closed-loop plasticity parameters, 0.8 s L1 `synapse_lif_v1` trials sample declared L3 states (daytime light `L=1`, evening clock drive `DN1p 40 Hz`, post-deprivation high `S` debt modeled via `ER5` `1.5x` outgoing efficacy modulation, and `50 Hz` misaligned light drive).
2. **Anatomically Grounded Target Cohorts on `malecns_v1_0` (`sleep001_malecns_v1_targets.json`):**
   - Drive optic/accessory medulla light relays (`70` `MeTu2a` `ACH`, `6` `aMe12` `ACH`) and dorsal clock outputs (`8` `DN1pA` `GLUT` + `4` `DN1pB` `GLUT`), reading out central-complex sleep-homeostat/navigation populations (`4` `ExR1` `ACH`, `21` `ER5` `GABA`, `10` `TuBu01` `ACH`, `10` `TuBu06` `ACH`, `46` `EPG` `ACH`) and evening clock targets (`4` `5thsLNv_LNd6` `ACH`, `4` `LNd_b` `ACH`).
3. **Matched Control Strategy & Transparent `ER5` Uniqueness Disclosure:**
   - Select `12` `cb_intrinsic` `GLUT` matched controls for `dn1p_all_clock` (`12` `GLUT`) excluding all sleep/clock core nodes and 1-hop presynaptic partners of `TuBu01`, `TuBu06`, `TuTuB_b`, `ExR1`, `ER5`, `5thsLNv_LNd6`, and `LNd_b` (`|SMD| <= 0.0304`, `0` direct edges onto readouts).
   - Explicitly document in [`evidence_register.md`](../../research/modules/sleep/evidence_register.md) that `ER5` ring neurons possess an anomalously high outgoing-synapse-to-degree ratio (`|SMD| > 2.0` against other `cb_intrinsic` `GABA` and even non-`ER5` `ER*` ring neurons), so `ER5` perturbations are benchmarked internally via pathway-selective `EdgeMaskModulation(ER5 -> ExR1)` rather than an ill-matched `GABA` cell-ablation control.

## Consequences

- Negative controls work at both scales: breaking L3 light transduction (`v_dT_light = 2.0`) fails verification gates and blocks shift-work execution; in L1, `DN1p` vs. `matched_cb_glut_controls` (`|SMD| <= 0.0304`) isolates clock-pathway specificity.
- Unvalidated behavioral equivalence, neuromodulator/neuropeptide omissions (`PDF`, `SIFa`, `l-LNv` `UNKNOWN`, `DA`, `OCT`, `SER` with `0.0` L1 synaptic weight), and single-specimen limits remain explicitly surfaced in documentation and UI banners.
