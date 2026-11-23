# Model Card: `sleep` Module (`leloup_goldbeter_1998_two_process_v1` L3 + `synapse_lif_v1` L1 on `malecns_v1_0`)

> **Research Use Only (RUO):** Combines a verified L3 biochemical-homeostatic differential equation model with quasi-steady-state L1 whole-CNS LIF probes on `malecns_v1_0`. **Not** a clinical sleep model or validated behavioral sleep predictor (`AGENTS.md` §7.1, §10).

## 1. L3 Circadian-Homeostatic Oscillator (`leloup_goldbeter_1998_two_process_v1`)

- **Model Identity:** `model_id = "leloup_goldbeter_1998_two_process_v1"`, `revision = "1.0"`, `model_level = "L3"`, canonical parameter manifest SHA-256 `348fc343c91a2d709bbda918492dc5a52a7758be1f8f350fd01d0dd1f0622c23`.
- **Implementation:** `packages/synapse_core/circadian.py` (`CircadianHomeostaticParameters`, `simulate_two_process`, `verify_circadian_homeostatic_gates`, `run_shift_work_experiment`).
- **Equations & Units:**
  - **Molecular Clock (10 ODEs, time `h`, concentrations `nM`):** Exact Leloup & Goldbeter (1998) `BIOMD0000000021` `per`/`tim` transcription-translation feedback loop (`v_sP = v_sT = 1.0`, `v_mP = v_mT = 0.7`, `k_sP = k_sT = 0.9`, `k1 = 0.6`, `k2 = 0.2`, `k3 = 1.2`, `k4 = 0.6`, `n_hill = 4.0`), integrated with `scipy.integrate.solve_ivp` (`RK45`, `rtol = 1e-8`, `atol = 1e-10`, `max_step_h = 0.1 h`, `dt_eval_h = 0.05 h = 180 s`). Light schedule modulates `TIM` degradation between `v_dT_dark = 2.0 nM/h` and `v_dT_light = 4.0 nM/h`.
  - **Homeostatic Process `S` (dimensionless `[0, 1]`):** Exact exponential buildup during `wake_proxy` (`tau_i_h = 8.76 h`) and decay during `quiescence_rest_proxy` (`tau_d_h = 9.51 h`; Abhilash & Shafer 2024 *Drosophila* fit) with circadian-gated thresholds `U(t) = 0.65 + 0.12 * c_wake(t)` and `L(t) = 0.35 + 0.12 * c_wake(t)` where `c_wake = clip(-(C_N - 1.15) / 0.70, -1.2, 1.2)`.
- **Verified Pre-Shift-Work Gates:** All 4 quantitative gates passed before shift-work execution (`tau_DD = 24.1346 h`, convergence diff `0.0 h`, `tau_LD = 24.0171 h`, `CT 15` delay `-2.3591 h`, `CT 21` advance `+2.3431 h`, `CT 3–9` dead zone `<= 0.0035 h`, 12 h deprivation rebound `+0.1625` rest fraction, Day-9 washout `-0.0042`).
- **Negative Control Gate:** Disabling light sensitivity (`v_dT_light = 2.0`) fails LD/PRC gates and causes `run_shift_work_experiment(..., require_verified_gate=True)` to raise `RuntimeError`.

## 2. L1 Connectome-Grounded Circuit Probe (`synapse_lif_v1` on `malecns_v1_0`)

- **Model Identity:** `synapse_lif_v1` (`revision = "1.0"`, SHA-256 `33d49431529574cddc721a3628ed1c65ad2e36890e2720fe6ef921837348bece`), `brian2_cpu` (`solver = "exact"`, `dt = 0.0001 s`, `tau_m = 20 ms`, `tau_syn = 5 ms`, `t_ref = 2.2 ms`, `delay = 1.8 ms`, `w_syn_v = 0.275 mV`, `unknown_nt_policy = "zero_effect"`).
- **L3 -> L1 Timescale Interface (Quasi-Steady-State):** Because L3 evolves on `180 s` (`0.05 h`) steps over `16` days (`384 h`) while L1 integrates at `0.1 ms` over `0.8 s` (`stim_window = [0.1, 0.6) s`), L1 conditions probe discrete steady-state snapshots mapped from L3 regimes (`light_day_baseline`, `light_plus_clock_dn1p_drive`, `light_plus_er5_high_homeostat_gain`, `shift_light_misaligned_clock_debt`) alongside structural masks (`dn1p_avp_edge_mask`, `er5_exr1_edge_mask`), `sham_zero_stimulus`, and `12` matched `cb_intrinsic` `GLUT` controls (`|SMD| <= 0.0304`).
- **Assumptions & Limits:** Single male connectome, binary excitatory (`ACH`) vs. inhibitory (`GABA`, `GLUT`) sign mapping in L1, `0.0` weight on `UNKNOWN`/`HIST`/`DA`/`OCT`/`SER`, and absence of slow metabotropic sleep-debt plasticity in L1 membrane equations.
