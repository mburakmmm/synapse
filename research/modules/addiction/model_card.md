# Model Card: `addiction` Module (`mb_dopamine_plasticity_v1` L2 + `synapse_lif_v1` L1 on `malecns_v1_0`)

> **Research Use Only (RUO):** Couples a verified L2 continuous-time three-factor mushroom-body plasticity ODE model (`mb_dopamine_plasticity_v1`) to whole-CNS L1 LIF connectome snapshots on `malecns_v1_0`. **Not** a clinical dependence, craving, or diagnostic addiction model (`AGENTS.md` §1, §7.1, §10).

## 1. L2 Mushroom-Body Three-Factor Plasticity Kernel (`mb_dopamine_plasticity_v1`)

- **Model Identity:** `model_id = "mb_dopamine_plasticity_v1"`, `revision = "1.0"`, `model_level = "L2"`, canonical parameter manifest SHA-256 `ca302818cd9281529831192317dc78131b537327a398fad1c64c02fef8c402b4`.
- **Implementation:** `packages/synapse_core/plasticity.py` (`MBPlasticityParameters`, `simulate_conditioning_schedule`, `verify_plasticity_paradigm_gates`, `run_conditioning_paradigm`).
- **Equations & Units:**
  - **Eligibility & Dopamine Traces (`s`, normalized dimensionless states):** `de_c/dt = (-e_c + r_kc_c(t)) / tau_e_s` (`tau_e_s = 4.0 s`), `dd_pam/dt = (-d_pam + u_reward(t)) / tau_d_s`, `dd_ppl1/dt = (-d_ppl1 + u_omission(t)) / tau_d_s` (`tau_d_s = 1.5 s`), where unreinforced `CS+` omission triggers prediction-error `u_omission = 1.2 * sum_c max(0, w_init - w_avoid_c) * r_kc_c(t)` when `u_reward == 0.0`.
  - **Parallel Opposing Synaptic Weights (`w in [0.15, 1.0]`):**
    - `dw_avoid_c/dt = -eta_ltd_pam * e_c * d_pam * (w_avoid_c - w_min) + (w_init - w_avoid_c) / tau_rec_avoid_s` (`eta_ltd_pam = 0.09`, `tau_rec_avoid_s = 1500.0 s`).
    - `dw_appr_c/dt = -eta_ltd_ppl1 * e_c * d_ppl1 * (w_appr_c - w_min) + eta_pot_reinst * d_pam * (w_init - w_appr_c) + (w_init - w_appr_c) / tau_rec_appr_s` (`eta_ltd_ppl1 = 0.10`, `eta_pot_reinst = 0.08`, `tau_rec_appr_s = 150.0 s`).
  - **Readout & Preference Index Proxy (`PI in [-1, +1]`):** `R_avoid(c) = 40.0 * w_avoid_c`, `R_appr(c) = max(0, 40.0 * w_appr_c - 0.25 * R_avoid(c))`, `V(c) = (R_appr - R_avoid) / (R_appr + R_avoid + 1e-6)`, `PI = 0.5 * (V(CS+) - V(CS-))`.
  - **Integration & Conditioning Schedule (`310.0 s`):** Explicit 4th-order Runge-Kutta (`RK4`, `dt_s = 0.05 s`) over Naive `[0, 10) s`, Acquisition `[10, 145) s`, Extinction `[145, 235) s`, and Reinstatement/Recovery `[235, 310] s`.
- **Verified Pre-Experiment Gates (5/5 PASS):**
  - `dt/2` convergence: `max|dW| = 1.947e-4 < 1e-3`, `max|dPI| = 7.855e-5 < 1e-3`, strict `[0.15, 1.0]` bounds.
  - Acquisition (`145 s`): `PI_acq = +0.33123`, `w_avoid(CS+) = 0.292978`, `|w_avoid(CS-) - 1.0| = 0.0`.
  - Parallel Extinction (`235 s`): `PI_ext = +0.045171` (`drop = 0.286059`), `w_appr(CS+) = 0.384344`, original reward trace preserved (`w_avoid(CS+) = 0.334152`).
  - Reinstatement (`310 s`): `PI_reinst = +0.26580` (`gain = +0.220629`, exceeding passive spontaneous recovery `+0.16480`), `w_appr(CS+) = 0.924609`.
  - Negative controls: `sham = 0.0`, `yoked_unpaired PI_acq = 6.2e-5`, `dan_blocked = 0.0`. Disabling `eta_ltd_pam = 0.0` or `tau_e_s = 1000.0 s` raises `RuntimeError` fail-closed.

## 2. L1 Connectome-Grounded Circuit Probe (`synapse_lif_v1` on `malecns_v1_0`)

- **Model Identity:** `synapse_lif_v1` (`revision = "1.0"`, SHA-256 `33d49431529574cddc721a3628ed1c65ad2e36890e2720fe6ef921837348bece`), `brian2_cpu` (`solver = "exact"`, `dt = 0.0001 s`, `w_syn_v = 0.275 mV`, `unknown_nt_policy = "zero_effect"`).
- **L2 -> L1 Weight Snapshot Interface:** Because L2 evolves over `310 s` conditioning trials while L1 evaluates `0.6 s` network snapshots (`stim = [0.1, 0.6) s`), L1 conditions apply exact L2 weight snapshots (`0.292978`, `0.334152 / 0.384344`, `0.366625 / 0.924609`) as `EdgeMaskModulation` onto `cs_plus_kcs -> mbon_avoid/approach_readouts`, paired with Hungarian-matched `matched_ctrl_kcs` (`|SMD| <= 0.13225`), `cs_minus_kcs`, and `sham_zero_stimulus`.
- **Assumptions & Limits:** Single male specimen, binary excitatory (`ACH`) vs. inhibitory (`GABA`/`GLUT`) L1 weights, `0.0` fast weight on `DA`/`OCT`/`SER`, and somatic `APL` clamping on `MBON01/05/11`.
