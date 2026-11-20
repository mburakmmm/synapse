# Working Manuscript Outline: `MET-001` Presynaptic Gustatory Gain in FlyWire v630

> **DRAFT MANUSCRIPT PACKAGE (`AGENTS.md` §12):** All quantitative values trace directly to verified artifacts on disk (`P2-BENCH-SHIU2024`, `P4-MET-001-PILOT`, `P4-MET-001.frozen.yaml`, `P4-MET-001-ROBUST-*`). Authorship, CRediT roles, conflict declarations, funding, ethics determination, and external publication require explicit human review and approval.

## 1. Research Scope & Non-Clinical Disclaimer

- **Organism & Model Scope:** Adult female *Drosophila melanogaster* (`flywire_fafb_v630`), reduced L1 LIF connectome model (`shiu2024_lif`, Research Use Only). Carries zero human clinical, BMI, insulin-resistance, or diagnostic claims.

## 2. Prior Reproduction Gate & Biological Grounding

- Reproduced `SHIU2024-FEEDING-BENCHMARK` (`90/90` runs on `flywire_fafb_v630`, `overall_passed=true`, `MN9_right = 68.833 ± 4.243 Hz` at `100 Hz` sugar drive; [`shiu2024_reproduction_report.md`](../../docs/validation/shiu2024_reproduction_report.md)).
- Literature basis linking starvation-regulated dopaminergic sensory gain and gustatory connectivity segregation is cataloged in [`source_register.yaml`](../literature/source_register.yaml) and [`evidence_register.md`](../modules/metabolic/evidence_register.md).

## 3. Methods (`P4-MET-001.frozen.yaml`, `d15ad4aafe10...`)

- **Targets & Matched Controls:** `21` right sugar GRNs (`EXCITATORY_SIGN`) paired 1-to-1 against `21` non-gustatory `EXCITATORY_SIGN` controls excluding MN9 and 1-hop sugar-GRN targets via [`controls.py`](../../packages/synapse_experiments/controls.py) (`|smd| <= 0.0431`; [`met001_flywire_v630_targets.json`](../modules/metabolic/target_sets/met001_flywire_v630_targets.json)).
- **Exploratory Calibration Disclosure:** Pilot [`P4-MET-001-pilot.yaml`](../protocols/P4-MET-001-pilot.yaml) (`master=20261121`, `N=3`) calibrated sub-maximal `50 Hz` input; documented separately in [`pilot_report.md`](../modules/metabolic/pilot_report.md).
- **Locked Confirmatory Execution:** `6` conditions × `30` paired seeds (`master=20261122`, `180/180` succeeded, `0` failed, `3449.42 s` wall).

## 4. Confirmatory & Robustness Results

- **Controls Passed:** `sham_zero_stimulus` emitted `0` total spikes across all `30` seeds; `sugar_100hz_positive_control` produced `MN9_right = 67.800 ± 4.723 Hz` and `MN9_left = 49.067 ± 3.140 Hz` (`100 Hz` Phase 2 ref: `67.033` / `48.633 Hz`).
- **Primary Endpoint (`MN9_right`):**
  - `1.25x` gain vs `50 Hz` baseline (`42.200` vs `20.200 Hz`): paired Δ `+22.0000 ± 7.7415 Hz`, 95% bootstrap CI `[+19.2667, +24.7342] Hz`, BH-FDR $q = 9.999 \times 10^{-5}$.
  - `1.50x` gain vs `50 Hz` baseline (`51.100` vs `20.200 Hz`): paired Δ `+30.9000 ± 7.1936 Hz`, 95% bootstrap CI `[+28.2333, +33.3667] Hz`, BH-FDR $q = 9.999 \times 10^{-5}$.
  - `1.50x` matched non-gustatory control vs `50 Hz` baseline (`20.200` vs `20.200 Hz`): Δ `0.0000 Hz` (`deterministic_zero_difference`); specificity contrast `gain_1p50 - matched_ctrl_gain_1p50` = `+30.9000 Hz` ($q = 9.999 \times 10^{-5}$).
- **Secondary Endpoint (`MN9_left`):** `+16.0667 Hz` (`1.25x`) and `+23.6667 Hz` (`1.50x`); seed SE converges from `2.4900` (`k=5`) to `1.3134 Hz` (`k=30`).
- **Sensitivity Arms (`N=6`, `master=20261123`):** Positive `+1.50x` Δ persisted under `synapse_lif_v1` (`+34.667 Hz`, $p=0.03125$), `w_syn_v = 0.2475 mV` (`+31.500 Hz`), and `w_syn_v = 0.3025 mV` (`+23.500 Hz`), while absolute `50 Hz` baseline varied strongly with `w_syn_v` (`4.500` to `38.833 Hz`); see [`confirmatory_report.md`](../modules/metabolic/confirmatory_report.md).
- **Figure Source Bundles:** `runs/phase4_met001_confirmatory/bundle_mn9r_{gain_1p50,specificity,gain_1p25}` and `bundle_mn9l_gain_1p50`.

## 5. Limitations & Governance Placeholders

- L1 synapse-count scaling without GPCR/endocrine kinetics; silent `-52 mV` baseline explains exact `0.000 Hz` matched-control shift; `malecns_v1_0` lacks annotated sugar-GRN modality tags for direct male cross-connectome replication without guessing.
- **Human Sign-Off Required:** Authors / CRediT / Ethics / Conflict / Funding / AI-Assistance Disclosure (`Antigravity` coding/workflow assistant): `[TO BE COMPLETED BY HUMAN AUTHORS BEFORE ARCHIVING OR SUBMISSION]`.
