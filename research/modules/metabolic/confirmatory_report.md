# Confirmatory & Robustness Report: `P4-MET-001` (`metabolic`)

> **RESEARCH USE ONLY (RUO):** Confirmatory simulation analysis conditional on frozen [`P4-MET-001.frozen.yaml`](../../protocols/P4-MET-001.frozen.yaml), `flywire_fafb_v630` sign-only connectivity, and reduced L1 `LIF` equations. **Not** wet-lab biological validation or clinical/human medical evidence.

## 1. Frozen Protocol & Provenance

- **Approved Draft Protocol:** [`P4-MET-001.yaml`](../../protocols/P4-MET-001.yaml) (`revision: 1`, `status: approved`)
- **Frozen Confirmatory Protocol:** [`P4-MET-001.frozen.yaml`](../../protocols/P4-MET-001.frozen.yaml) (`frozen_at_utc: 2026-11-20T18:45:44.305747+00:00`, `protocol_sha256: d15ad4aafe1088fa1bc6afb62b58528b27e948c1f2d07c3484963eebb00bef05`, `master_seed: 20261122`, `replicates: 30`)
- **Prior Exploratory Pilot Disclosure:** Calibrated stimulus drive (`50 Hz`) using [`P4-MET-001-pilot.yaml`](../../protocols/P4-MET-001-pilot.yaml) (`master_seed: 20261121`, `N=3`) documented in [`pilot_report.md`](pilot_report.md).
- **Dataset & Model:** `flywire_fafb_v630` (`v630`, manifest `f6965c945c801571371f6f593cdc9d1fc2f6cb8cbe32def898d1640069b4acf9`), `shiu2024_lif` v`1.0` (`parameter_manifest_sha256: 12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`, `brian2_cpu` `numpy`).
- **Matched Control Artifact:** [`met001_flywire_v630_targets.json`](target_sets/met001_flywire_v630_targets.json) (`21` sugar GRNs vs `21` non-gustatory `EXCITATORY_SIGN` controls excluding MN9 & 1-hop targets; all `|smd| <= 0.0431`).
- **Execution Completeness (`runs/phase4_met001_confirmatory/`):** `180/180` runs succeeded (`failed_run_count = 0`), `CONFIRMATORY_WALL_SECONDS = 3449.42 s` (`~57.49 min`), per-run wall `51.42–70.97 s` (mean `56.38 s`).

## 2. Condition Summaries & Control Checks (`N = 30` per condition)

| Condition | Total Spikes / Control Check | `MN9_right` Mean ± Samp SD (Hz) | `MN9_right` Med (IQR) | `MN9_left` Mean ± Samp SD (Hz) |
|---|---|---:|---:|---:|
| `sham_zero_stimulus` | `max_total_spikes = 0` (`30/30` runs) | `0.000 ± 0.000` | `0.000 (0.000)` | `0.000 ± 0.000` |
| `sugar_100hz_positive_control` | Ref Phase 2: `67.033` / `48.633` Hz | `67.800 ± 4.723` | `67.500 (6.000)` | `49.067 ± 3.140` |
| `sugar_50hz_baseline` | Unmodulated `50 Hz` sucrose drive | `20.200 ± 6.456` | `20.000 (7.750)` | `15.567 ± 5.399` |
| `sugar_50hz_grn_gain_1p25` | `1.25x` outgoing sugar-GRN gain | `42.200 ± 5.653` | `42.000 (8.750)` | `31.633 ± 4.597` |
| `sugar_50hz_grn_gain_1p50` | `1.50x` outgoing sugar-GRN gain | `51.100 ± 5.326` | `51.000 (6.750)` | `39.233 ± 4.644` |
| `sugar_50hz_matched_ctrl_gain_1p50` | `1.50x` gain on 21 matched controls | `20.200 ± 6.456` | `20.000 (7.750)` | `15.567 ± 5.399` |

## 3. Confirmatory Paired Contrasts & Multiplicity Control (`N = 30` pairs)

| Endpoint | Contrast (`treatment - baseline`) | Mean Δ (Hz) | SD (Hz) | 95% Bootstrap CI (Hz) | Permutation $p$ | BH-FDR $q$ |
|---|---|---:|---:|---|---:|---:|
| `MN9_right` (Primary) | `gain_1p50 - baseline` | `+30.9000` | `7.1936` | `[+28.2333, +33.3667]` | `9.999e-05` (`MC, 10k`) | **`9.999e-05`** |
| `MN9_right` (Primary) | `gain_1p50 - matched_ctrl_gain_1p50` | `+30.9000` | `7.1936` | `[+28.2333, +33.3667]` | `9.999e-05` (`MC, 10k`) | **`9.999e-05`** |
| `MN9_right` (Primary) | `gain_1p25 - baseline` | `+22.0000` | `7.7415` | `[+19.2667, +24.7342]` | `9.999e-05` (`MC, 10k`) | **`9.999e-05`** |
| `MN9_right` (Control) | `matched_ctrl_gain_1p50 - baseline` | `0.0000` | `0.0000` | `[0.0000, 0.0000]` | `1.0` (`det_zero_diff`) | — |
| `MN9_left` (Secondary) | `gain_1p50 - baseline` | `+23.6667` | `7.3688` | `[+20.9333, +26.1667]` | `9.999e-05` (`MC, 10k`) | — |
| `MN9_left` (Secondary) | `gain_1p25 - baseline` | `+16.0667` | `6.8326` | `[+13.6000, +18.3333]` | `9.999e-05` (`MC, 10k`) | — |

- **Monotonic Gain Sensitivity (`1.00 -> 1.25 -> 1.50`):** `MN9_right` rises monotonically from `20.200` to `42.200` to `51.100 Hz` (`endpoint_range = 30.900 Hz`); `MN9_left` rises monotonically from `15.567` to `31.633` to `39.233 Hz` (`endpoint_range = 23.667 Hz`).
- **Monte Carlo Seed Convergence (`MN9_right`, `gain_1p50 - baseline`):**
  - `k=5`: `34.0000` (SE `2.4900`), `k=10`: `31.3000` (`1.5780`), `k=15`: `29.6667` (`1.8249`), `k=20`: `30.8500` (`1.5171`), `k=25`: `30.4800` (`1.5515`), `k=30`: `30.9000` (`1.3134` Hz).
- **Evidence Bundles Exported (`runs/phase4_met001_confirmatory/`):** `bundle_mn9r_gain_1p50`, `bundle_mn9r_specificity`, `bundle_mn9r_gain_1p25`, `bundle_mn9l_gain_1p50` (`failed_run_count = 0`).

## 4. Exploratory Robustness & Sensitivity Arms (`36` runs, `master = 20261123`)

| Arm | `n` Pairs | `50Hz Base` (Hz) | `Gain 1.50x` (Hz) | Paired Δ ± SD (Hz) | Exact Sign-Flip $p$ | Wall (s) |
|---|---:|---:|---:|---:|---:|---:|
| [`canonical_lif`](../../protocols/P4-MET-001-robust-canonical-lif.yaml) (`dg_unless_refractory=false`, `solver=exact`) | `6` | `22.667 ± 6.218` | `57.333 ± 5.086` | `+34.667 ± 9.026` (`[28.500, 41.000]`) | `0.03125` | `291.38` |
| [`wsyn_low`](../../protocols/P4-MET-001-robust-wsyn-low.yaml) (`w_syn_v = 0.2475 mV`, `-10%`) | `6` | `4.500 ± 2.429` | `36.000 ± 8.626` | `+31.500 ± 9.503` (`[25.167, 38.833]`) | `0.03125` | `259.34` |
| Nominal Confirmatory (`w_syn_v = 0.2750 mV`, `shiu2024_lif`) | `30` | `20.200 ± 6.456` | `51.100 ± 5.326` | `+30.900 ± 7.194` (`[28.233, 33.367]`) | `9.999e-05` | — |
| [`wsyn_high`](../../protocols/P4-MET-001-robust-wsyn-high.yaml) (`w_syn_v = 0.3025 mV`, `+10%`) | `6` | `38.833 ± 3.920` | `62.333 ± 4.546` | `+23.500 ± 7.477` (`[17.333, 28.333]`) | `0.03125` | `250.12` |

- **`w_syn_v` Sensitivity (`0.2475 -> 0.2750 -> 0.3025 mV`):** Baseline `50 Hz` MN9 rate increases strongly with `w_syn_v` (`4.500` → `20.200` → `38.833 Hz`, range `34.333 Hz`), while the `+1.50x` incremental Δ narrows slightly toward saturation (`31.500` → `30.900` → `23.500 Hz`, range `8.000 Hz`, `monotone_decreasing`) while staying strictly positive across all model variants (`ROBUSTNESS_TOTAL_WALL_SECONDS = 811.89 s`).

## 5. Cross-Connectome Inspection (`malecns_v1_0`) & Scientific Limitations

- Querying `data/curated/malecns_v1_0/curated/neurons.parquet` found `2` `MN9` motor neurons (`16949` `R`, `10331` `L`) and `60` taste-peg `GRN` cells (`50` `claw_tpGRN`, `10` `dorsal_tpGRN`), with `0` cells labeled `sugar`, `gustatory`, `Gr5a`, or `Gr64`. Per `AGENTS.md §1–2`, MaleCNS lacks verified sugar-GRN modality assignments in this canonical annotation release, so no guessed node mapping or pooled cross-specimen run was fabricated.
- Because L1 `shiu2024_lif` rests silently (`-52 mV`) without background noise, un-driven non-gustatory matched controls induce `0.000 Hz` delta; specificity here demonstrates structural routing selectivity under sucrose input, not modulation of tonic spontaneous circuits in vivo.
