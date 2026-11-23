# ADR-0008: Phase 5B Addiction Module — L2 Three-Factor MB Plasticity & L1 `malecns_v1_0` Coupling

- **Status:** Accepted (Phase 5B L2 Plasticity Gates Verified + L1 Exploratory Pilot Architecture; Confirmatory Freeze Pending Human Approval)
- **Date:** 2026-11-23
- **Owners:** SYNAPSE Maintainers

## Context

`AGENTS.md` §1, §2, §7.1, §10, and §15 require that the **Addiction** module (`addiction`):
1. Implement and verify an explicit **L2 synaptic plasticity rule and conditioning paradigm** prior to whole-brain circuit perturbations.
2. Strictly separate **acquisition**, **extinction**, and **reinstatement/recovery**, incorporating explicit **yoked/unpaired**, **sham**, and **dopamine-blocked** negative controls alongside odor specificity (`CS-`).
3. Keep all outcomes strictly **Research Use Only (RUO)** *Drosophila melanogaster* proxies (`learned preference index proxy PI`, `MBON avoidance/approach balance`), never claiming human clinical dependence, craving, or diagnosis, and never pooling `malecns_v1_0` with `flywire_fafb_v630`.

## Decision

1. **Dual-Scale L2 + L1 Architecture (`packages/synapse_core/plasticity.py` + `Brian2CPUBackend`):**
   - **L2 Three-Factor MB Plasticity Kernel (`mb_dopamine_plasticity_v1`, `sha256: ca302818cd9281529831192317dc78131b537327a398fad1c64c02fef8c402b4`):** Integrates Kenyon-cell coincidence eligibility traces (`tau_e_s = 4.0 s`), reward `PAM` dopamine transients (`tau_d_s = 1.5 s`), and omission-driven `PPL1` dopamine prediction errors (`omission_gain = 1.2`) across two opposing output compartments (`w_avoid` on glutamatergic `MBON02/04`; `w_appr` on cholinergic `MBON12/14/18`) with feedforward cross-compartment inhibition (`g_cross = 0.25`) reflecting the verified `380`-synapse `MBON02 (GLUT) -> MBON14 (ACH)` connection in `malecns_v1_0`.
   - **Parallel-Memory Extinction:** Rather than erasing the acquired `KC -> MBON_avoid` reward depression (`w_avoid_cs_plus = 0.292978 -> 0.334152`), unreinforced `CS+` omission drives `PPL1`-mediated depression onto the opposing `KC -> MBON_appr` pathway (`w_appr_cs_plus = 1.0 -> 0.384344`), reducing `PI` (`+0.33123 -> +0.045171`). Unconditioned `PAM` re-exposure potentiates `w_appr_cs_plus` back to `0.924609` (`PI = +0.26580`), exceeding passive spontaneous recovery (`PI = +0.16480`).
   - **Pre-Experiment Gate Enforcement:** `run_conditioning_paradigm(..., require_verified_gate=True)` enforces all 5 gates (`dt/2` convergence, `CS+` acquisition & `CS-` invariance, parallel-memory extinction preserving `w_avoid`, reinstatement recovery, and `sham`/`yoked_unpaired`/`dan_blocked` null controls).
2. **Anatomically Grounded `malecns_v1_0` Cohorts (`add001_malecns_v1_targets.json`):**
   - Isolate `143` `DM1_lPN + DM4_adPN`-selective `CS+` KCs, `143` exact `(cell_type, soma_side)` Hungarian-matched unresponsive control KCs (`|SMD| <= 0.13225`, `0` synapses from `PN_A` or `PN_B`), and `143` disjoint `DC1_adPN + VA2_adPN`-selective `CS-` KCs.
   - Sample frozen `l2_to_l1_weight_snapshots` in `P5-ADD-001-pilot.yaml` via pathway-selective `EdgeMaskModulation` onto `MBON02/04` and `MBON12/14/18`.

## Consequences

- L1 whole-CNS LIF trials inherit fixed L2 synaptic weight snapshots (`naive`, `post_acquisition`, `post_extinction`, `post_reinstatement`, `yoked_matched_ctrl`) without inventing unverified online millisecond STDP kinetics.
- Somatic point-neuron `APL` GABAergic inhibition onto `MBON01` (`818` syn), `MBON05` (`1,162` syn), and `MBON11` (`441` syn) during early feedforward onset (`[0.1, 0.2) s`), as well as polysynaptic `CRE011/KCab` recurrent ignition across `[0.2, 0.6] s` when `APL` dendritic localization (`Lin et al. 2014`; `Amin et al. 2020`) is absent, are explicitly separated and documented in [`evidence_register.md`](../../research/modules/addiction/evidence_register.md) and [`pilot_report.md`](../../research/modules/addiction/pilot_report.md).
