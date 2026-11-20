# Exploratory Pilot Report: `P4-MET-001-PILOT` (NOT Confirmatory)

> **EXPLORATORY PILOT ONLY (`analysis_intent: exploratory`, `status: draft`, `N = 3` paired seeds):** Used strictly to calibrate sub-maximal drive (`50 Hz`) and inspect matched-control behavior prior to human review and freeze of [`P4-MET-001.yaml`](../../protocols/P4-MET-001.yaml). **Not** confirmatory hypothesis evidence and **not** wet-lab biological validation.

## 1. Provenance & Matched Control Balance

- **Dataset:** `flywire_fafb_v630` (`v630`, `is_synthetic_fixture=false`, manifest `f6965c945c801571371f6f593cdc9d1fc2f6cb8cbe32def898d1640069b4acf9`)
- **Model:** `shiu2024_lif` (`revision: 1.0`, `parameter_manifest_sha256=12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`)
- **Pilot Protocol:** [`P4-MET-001-pilot.yaml`](../../protocols/P4-MET-001-pilot.yaml) (`protocol_sha256=9481a66d750f74c2cff60adb1cb70e19e9f55dfc263c23625c6341b65c0b2096`, `master_seed=20261121`, `replicates=3`)
- **Run Execution:** `15/15` succeeded (`failed_run_count=0`, `PILOT_WALL_SECONDS=575.78 s`, `--workers 3`, `101.35–117.40 s` per run)
- **Matched Control Imbalance ([`met001_flywire_v630_targets.json`](target_sets/met001_flywire_v630_targets.json)):**
  - `out_degree`: targets mean `73.67` (SD `13.09`) vs controls `73.33` (SD `13.60`), `smd = -0.0250`
  - `out_synapses`: targets mean `353.81` (SD `152.87`) vs controls `347.57` (SD `135.91`), `smd = -0.0431`
  - `in_degree`: targets `33.19` vs controls `33.14`, `smd = -0.0058`
  - `in_synapses`: targets `186.29` vs controls `186.62`, `smd = +0.0058`
  - All 21 control neurons share `EXCITATORY_SIGN` and exclude both MN9 neurons and all 1-hop postsynaptic targets of sugar GRNs.

## 2. Observed Firing Rates (`N = 3` seeds)

- **Negative Sham Control (`sham_zero_stimulus`):** `total_spikes = [0, 0, 0]`; `MN9_right = 0.000 Hz`, `MN9_left = 0.000 Hz`.
- **`sugar_50hz_baseline`:** `MN9_right = [12.0, 14.0, 26.0] Hz` (mean `17.333 Hz`), `MN9_left = [10.0, 11.0, 22.0] Hz` (mean `14.333 Hz`).
- **`sugar_50hz_grn_gain_1p25`:** `MN9_right = [36.0, 36.0, 44.0] Hz` (mean `38.667 Hz`), `MN9_left = [24.0, 36.0, 38.0] Hz` (mean `32.667 Hz`).
- **`sugar_50hz_grn_gain_1p50`:** `MN9_right = [51.0, 43.0, 51.0] Hz` (mean `48.333 Hz`), `MN9_left = [36.0, 39.0, 38.0] Hz` (mean `37.667 Hz`).
- **`sugar_50hz_matched_ctrl_gain_1p50`:** `MN9_right = [12.0, 14.0, 26.0] Hz` (mean `17.333 Hz`), `MN9_left = [10.0, 11.0, 22.0] Hz` (mean `14.333 Hz`).

## 3. Paired Contrasts, Exact Permutation, BH-FDR & Sensitivity (`MN9_right`)

| Contrast (`treatment - baseline`) | Mean Δ (Hz) | SD (Hz) | 95% Bootstrap CI (Hz) | Exact Sign-Flip $p$ | BH-FDR $q$ |
|---|---:|---:|---|---:|---:|
| `gain_1p25 - baseline` | `+21.333` | `3.055` | `[+18.000, +24.000]` | `0.250` ($2/8$) | `0.333` |
| `gain_1p50 - baseline` | `+31.000` | `7.211` | `[+25.000, +39.000]` | `0.250` ($2/8$) | `0.333` |
| `matched_ctrl_1p50 - baseline` | `0.000` | `0.000` | `[0.000, 0.000]` | `1.000` (`deterministic_zero_difference`) | `1.000` |
| `gain_1p50 - matched_ctrl_1p50` | `+31.000` | `7.211` | `[+25.000, +39.000]` | `0.250` ($2/8$) | `0.333` |

- **1D Local Sensitivity (`sugar_grn_outgoing_gain` over `[1.0, 1.25, 1.50]`):** `trend = "monotone_increasing"`, `endpoint_range = 31.000 Hz`.
- **Evidence Bundles:** `runs/phase4_met001_exploratory_pilot/bundle_gain_1p50/` and `bundle_specificity/` exported (`failed_run_count = 0`).

## 4. Honest Limitations & Statistical Note

1. **Zero Spontaneous Baseline Activity in L1 `shiu2024_lif`:** Because unstimulated neurons rest below threshold (`-52 mV < -45 mV`) with zero background noise, gain scaling on matched non-gustatory controls produces `0.000 Hz` shift on `MN9`. Thus the specificity contrast isolates connectome routing selectivity from driven GRNs rather than modulation under tonic spontaneous activity.
2. **Sample-Size Resolution ($N=3$):** With $2^3 = 8$ sign-flip combinations, minimum two-sided exact permutation $p = 0.25$ ($q = 0.333$), so $N=3$ cannot satisfy $q < 0.01$ despite consistent positive paired shifts. Confirmatory evaluation requires human approval and freezing of `P4-MET-001.yaml` (`N=30`, independent `master=20261122`).
