# Phase 5A Confirmatory & Robustness Report (`P5-PAIN-001`)

> **Research Use Only (RUO) & Claim Boundary:** This document reports **computational simulations conditional on the static `malecns_v1_0` connectome graph and `synapse_lif_v1` / `shiu2024_lif` Leaky Integrate-and-Fire (LIF) equations**. Confirmatory stochastic seed replication (`N = 15`, `q < 0.001`) establishes simulation reproducibility under the pre-registered protocol, **not** wet-lab biological validation, chronic transcriptional injury remodeling, or human pain equivalence ([`AGENTS.md`](../../../AGENTS.md) §2, §10).

---

## 1. Frozen Protocol & Execution Provenance

| Artifact / Field | Observed Value |
|---|---|
| Approved Protocol | [`P5-PAIN-001.yaml`](../../protocols/P5-PAIN-001.yaml) (`revision: 1`, `analysis_intent: confirmatory`) |
| Immutable Frozen Spec | [`P5-PAIN-001.frozen.yaml`](../../protocols/P5-PAIN-001.frozen.yaml) |
| `frozen_at_utc` | `2026-11-21T09:14:34.230135+00:00` |
| `protocol_sha256` | `a379c7e1c7b264859fe777730464cd8d34807dc1772818b5c4bb4b978ed683cf` |
| Dataset Specimen | `malecns_v1_0` (`v1.0`, `manifest_sha256: 6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`, single adult male CNS; `211,577` bodies, `26,028,386` edges, `125,365,933` synapses; never pooled with female FlyWire) |
| Reference Model | `synapse_lif_v1` (`revision: 1.0`, `parameter_manifest_sha256: 33d49431529574cddc721a3628ed1c65ad2e36890e2720fe6ef921837348bece`, `backend: brian2_cpu`, `solver: exact`, `dg_unless_refractory: false`, `w_syn_v: 0.000275 V`, `unknown_nt_policy: zero_effect`) |
| Seed Derivation | `master = 20261131`, `N = 15` paired seed replicates × `8` conditions (`120` runs) |
| Code Commit / Tree | `5a878cdd72cee9823f708c76d4058488f7051577` (`git_dirty = false`) |
| Execution Completeness | `120 / 120` succeeded (`failed_run_count = 0`) |
| Sham Negative Control | `15 / 15` replicates produced `0` spikes (`sham_max_spikes = 0`) |
| Wall-Clock Runtime | `8271.70 s` (`~2.30 h`) total; per-run `178.12–284.66 s` (mean `204.68 s`) |
| Local Output Root (gitignored) | `runs/phase5_pain001_confirmatory/` |

### Target & Matched Control Integrity

Defined in [`pain001_malecns_v1_targets.json`](target_sets/pain001_malecns_v1_targets.json):
- **Mechanosensory Driver (`R-MesoLN`):** top `30` right middle-leg sensory afferents.
- **Feedforward VNC GABA Targets vs. Matched Controls:** `26` feedforward `GABA` interneurons receiving disynaptic/direct VNC pathways downstream of `R-MesoLN` vs. `26` degree-, synapse-, and neurotransmitter-matched non-target VNC `GABA` interneurons (`|SMD| <= 0.0970`), both selected with `0` direct outgoing edges onto the ascending readout panel (`ascending_readout_all`).
- **Simulation Design (`P5-PAIN-001`):** `8` conditions × `15` paired seeds: zero-stimulus sham, `20 Hz` baseline and global GABA silencing (`gaba_cell_death`), `40 Hz` baseline, `40 Hz` matched-control silencing (`matched_ctrl_ablation`), `40 Hz` 50% outgoing GABA attenuation (`gaba_atten_50pct`), `40 Hz` global GABA silencing (`gaba_cell_death`), and `40 Hz` pathway-selective GABA→target disinhibition via `EdgeMaskModulation` (`acute_edge_mask`, preserving baseline intra-GABA connectivity to avoid non-target network collapse).

---

## 2. Windowed Firing Rates & Post-Stimulus Persistence (`N = 15`)

Trial duration is `0.8 s` partitioned into pre-stimulus `[0.0, 0.1) s`, stimulus `[0.1, 0.6) s`, and post-stimulus `[0.6, 0.8] s` windows. Pre-stimulus `[0.0, 0.1) s` rates were `0.000 Hz` across all `8` conditions and `120` runs, and `sham_zero_stimulus` produced `0.000 Hz` throughout (`0` spikes across `15` replicates). Ascending readout targets `13166` and `14994` remained `0.000 Hz` in every condition.

| Condition (`N = 15`) | `523539` (`ANXXX027_L`) Stim Mean ± SD (Hz) | `523539` Post (Hz / ms) | `558778` (`AN08B012_R`) Stim Mean ± SD (Hz) | `558778` Post (Hz / ms) | `10592` (`AN08B012_L`) Stim Mean ± SD (Hz) | `15070` Stim Mean ± SD (Hz) | `804642` (`TTMn_L`) Stim Mean ± SD (Hz) | `800146` Stim Mean ± SD (Hz) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `mesoln_20hz_baseline` | `11.333 ± 3.754` | `0.000` (`0.00 ms`) | `11.600 ± 2.165` | `0.333` (`0.01 ms`) | `6.933 ± 3.011` | `0.133 ± 0.516` | `0.000 ± 0.000` (post `0.333`, `7.83 ms`) | `0.000 ± 0.000` |
| `mesoln_20hz_gaba_cell_death` | `16.400 ± 5.616` | `0.000` (`0.00 ms`) | `12.667 ± 2.225` | `0.333` (`0.11 ms`) | `5.067 ± 2.251` | `1.867 ± 1.922` | `0.400 ± 0.828` | `0.000 ± 0.000` |
| `mesoln_40hz_baseline` | `19.067 ± 4.464` | `0.000` (`0.00 ms`) | `21.600 ± 2.640` | `0.000` (`0.00 ms`) | `16.267 ± 2.251` | `0.400 ± 0.828` | `0.533 ± 1.187` | `0.000 ± 0.000` |
| `mesoln_40hz_matched_ctrl_ablation` | `19.067 ± 3.918` | `0.000` (`0.00 ms`) | `22.400 ± 2.414` | `0.000` (`0.00 ms`) | `16.000 ± 2.828` (post `0.333`, `0.15 ms`) | `0.400 ± 0.828` | `0.667 ± 1.234` | `0.000 ± 0.000` |
| `mesoln_40hz_gaba_atten_50pct` | `31.733 ± 4.061` | `0.000` (`0.00 ms`) | `23.467 ± 2.200` | `1.000` (`0.35 ms`) | `14.533 ± 2.669` | `0.800 ± 1.014` | `1.067 ± 1.280` | `0.133 ± 0.516` |
| `mesoln_40hz_gaba_cell_death` | `44.267 ± 3.918` | `1.000` (`0.52 ms`) | `22.533 ± 2.446` | `0.333` (`0.12 ms`) | `8.933 ± 3.195` (post `0.333`, `0.10 ms`) | `3.733 ± 1.668` | `1.200 ± 1.656` (post `0.333`, `7.99 ms`) | `0.133 ± 0.516` (post `0.333`, `10.76 ms`) |
| `mesoln_40hz_acute_edge_mask` | `51.467 ± 5.423` | `1.667` (`1.03 ms`) | `27.467 ± 2.200` | `0.667` (`0.16 ms`) | `18.533 ± 2.446` | `1.200 ± 1.014` | `0.667 ± 1.234` | `0.000 ± 0.000` |

Post-stimulus activity in `[0.6, 0.8] s` stayed minimal (`<= 1.667 Hz` mean rate and `<= 10.76 ms` mean tail persistence across all conditions), consistent with synaptic decay (`tau_syn = 5 ms`) and absence of intrinsic rebound/pacemaker conductances in `synapse_lif_v1`.

---

## 3. Primary Confirmatory Contrasts (`0.0–0.8 s`, BH-FDR Controlled)

Full-trial firing rates (`0.0–0.8 s`) evaluated across `15` paired seed replicates via `10,000`-draw Monte Carlo paired sign-flip permutation tests with Benjamini-Hochberg false discovery rate correction across the `6` pre-specified primary contrasts:

| Contrast ID | Neuron | Comparison (Treatment vs. Reference) | Baseline Mean ± SD (Hz) | Treatment Mean ± SD (Hz) | Paired Δ Mean ± SD (Hz) | Bootstrap 95% CI (Hz) | Raw `p` | BH-FDR `q` |
|---|---|---|---:|---:|---:|---|---:|---:|
| `p1_523539_edge_mask_vs_base` | `523539` | `acute_edge_mask` vs. `40hz_baseline` | `11.917 ± 2.790` | `32.583 ± 3.487` | `+20.667 ± 2.907` | `[+19.331, +22.167]` | `9.9990e-05` | `9.9990e-05` |
| `p2_523539_edge_mask_vs_ctrl` | `523539` | `acute_edge_mask` vs. `matched_ctrl_ablation` | `11.917 ± 2.449` | `32.583 ± 3.487` | `+20.667 ± 2.209` | `[+19.500, +21.750]` | `9.9990e-05` | `9.9990e-05` |
| `p3_523539_cell_death_vs_base` | `523539` | `gaba_cell_death` vs. `40hz_baseline` | `11.917 ± 2.790` | `27.917 ± 2.485` | `+16.000 ± 2.639` | `[+14.667, +17.333]` | `9.9990e-05` | `9.9990e-05` |
| `p4_523539_cell_death_vs_ctrl` | `523539` | `gaba_cell_death` vs. `matched_ctrl_ablation` | `11.917 ± 2.449` | `27.917 ± 2.485` | `+16.000 ± 2.175` | `[+14.917, +17.085]` | `9.9990e-05` | `9.9990e-05` |
| `p5_558778_edge_mask_vs_base` | `558778` | `acute_edge_mask` vs. `40hz_baseline` | `13.500 ± 1.650` | `17.333 ± 1.484` | `+3.833 ± 1.858` | `[+3.000, +4.833]` | `9.9990e-05` | `9.9990e-05` |
| `p6_558778_edge_mask_vs_ctrl` | `558778` | `acute_edge_mask` vs. `matched_ctrl_ablation` | `14.000 ± 1.509` | `17.333 ± 1.484` | `+3.333 ± 1.391` | `[+2.667, +4.000]` | `9.9990e-05` | `9.9990e-05` |

All `6` pre-specified primary contrasts cleared the BH-FDR gate at the minimum resolvable `10,000`-permutation resolution (`q = 9.9990e-05`, positive direction across every pair).

---

## 4. Secondary & Negative-Control Contrasts (`0.0–0.8 s`, `N = 15`)

| Contrast ID | Neuron | Baseline -> Treatment Mean (Hz) | Paired Δ Mean ± SD (Hz) | Bootstrap 95% CI (Hz) | Monte Carlo `p` |
|---|---|---:|---:|---|---:|
| `s_523539_40hz_atten50_vs_base` | `523539` | `11.917 -> 19.833` | `+7.917 ± 2.394` | `[+6.750, +9.085]` | `9.9990e-05` |
| `s_523539_40hz_ctrl_vs_base` | `523539` | `11.917 -> 11.917` | `0.000 ± 2.004` | `[-0.919, +1.000]` | `1.0000` |
| `s_523539_20hz_cell_death_vs_base` | `523539` | `7.083 -> 10.250` | `+3.167 ± 2.709` | `[+1.917, +4.583]` | `1.3999e-03` |
| `s_558778_40hz_cell_death_vs_base` | `558778` | `13.500 -> 14.167` | `+0.667 ± 2.106` | `[-0.250, +1.833]` | `0.3380` |
| `s_558778_40hz_atten50_vs_base` | `558778` | `13.500 -> 14.917` | `+1.417 ± 1.997` | `[+0.500, +2.500]` | `0.0176` |
| `s_558778_40hz_ctrl_vs_base` | `558778` | `13.500 -> 14.000` | `+0.500 ± 1.623` | `[-0.250, +1.333]` | `0.3544` |
| `s_558778_20hz_cell_death_vs_base` | `558778` | `7.333 -> 8.000` | `+0.667 ± 1.325` | `[+0.000, +1.333]` | `0.1240` |
| `s_10592_40hz_edge_mask_vs_base` | `10592` | `10.167 -> 11.583` | `+1.417 ± 1.940` | `[+0.500, +2.417]` | `0.0213` |
| `s_10592_40hz_cell_death_vs_base` | `10592` | `10.167 -> 5.667` | `-4.500 ± 2.535` | `[-5.667, -3.167]` | `2.9997e-04` |
| `s_804642_40hz_edge_mask_vs_base` | `804642` | `0.333 -> 0.417` | `+0.083 ± 0.572` | `[-0.167, +0.333]` | `1.0000` |
| `s_804642_40hz_cell_death_vs_base` | `804642` | `0.333 -> 0.833` | `+0.500 ± 0.921` | `[+0.083, +1.000]` | `0.1134` |

### Mechanistic Dissociation Summary

- **Matched-Control Specificity:** Silencing `26` degree/synapse/NT-matched VNC GABA interneurons produced null shifts on both `523539` (`Δ = 0.000 Hz`, `p = 1.0000`) and `558778` (`Δ = +0.500 Hz`, `p = 0.3544`), confirming that disinhibition gains depend on targeted topology rather than total GABA synapse loss.
- **Acute `EdgeMaskModulation` vs. Global `NeuronSilencing` Dissociation on `10592` (`AN08B012_L`):** Whereas pathway-selective `acute_edge_mask` moderately increased `10592` (`+1.417 Hz`, `p = 0.0213`), whole-cell `gaba_cell_death` significantly *reduced* `10592` (`-4.500 Hz`, `p = 2.9997e-04`) and left `558778` unchanged (`+0.667 Hz`, `p = 0.3380`), consistent with loss of upstream disinhibitory or excitatory relay motifs when soma-level GABA activity is silenced globally across all targets.
- **Dose-Response Scaling on `523539`:** Graded attenuation progressed monotonically in full-trial rate across `0%` (`11.917 Hz`), `50%` (`19.833 Hz`, `+7.917 Hz`), `100%` cell death (`27.917 Hz`, `+16.000 Hz`), and selective `acute_edge_mask` (`32.583 Hz`, `+20.667 Hz`), while `20 Hz` sensory stimulation under `gaba_cell_death` raised `523539` from `7.083` to `10.250 Hz` (`+3.167 Hz`, `p = 1.3999e-03`).
- **Escape Motor Target (`804642`, `TTMn_L`):** `TTMn_L` fired at `< 1 Hz` overall with no statistically significant disinhibition lift in either manipulation (`p = 1.0000` and `p = 0.1134`).

---

## 5. Convergence & Outgoing-GABA Sensitivity (`N = 15`)

- **Seed Convergence (`k = 5, 10, 15` full-trial paired Δ):**
  - `p1_523539_edge_mask_vs_base`: `k=5` `21.000 ± 2.710` (SE `1.212`), `k=10` `20.875 ± 2.209` (SE `0.698`), `k=15` `20.667 ± 2.907 Hz` (SE `0.751`)
  - `p3_523539_cell_death_vs_base`: `k=5` `18.000 ± 1.896` (SE `0.848`), `k=10` `16.000 ± 2.875` (SE `0.909`), `k=15` `16.000 ± 2.639 Hz` (SE `0.681`)
  - `p5_558778_edge_mask_vs_base`: `k=5` `4.250 ± 2.878` (SE `1.287`), `k=10` `3.750 ± 2.282` (SE `0.722`), `k=15` `3.833 ± 1.858 Hz` (SE `0.480`)
- **Outgoing-GABA Factor Sensitivity (`1.0 -> 0.5 -> 0.0`, stimulus window):**
  - `523539`: baseline `19.067 Hz` to `44.267 Hz` (`endpoint_range = 25.200 Hz`, `monotone_decreasing` with active GABA fraction)
  - `558778`: `21.600 -> 23.467 -> 22.533 Hz` (`endpoint_range = 1.867 Hz`, `non_monotone`)
  - `10592`: `16.267 -> 14.533 -> 8.933 Hz` (`endpoint_range = 7.333 Hz`, `monotone_increasing` with active GABA fraction)

---

## 6. Exploratory Structural & Parametric Robustness (`N = 6`, `36 / 36` Runs)

Executed after confirmatory freeze using `master = 20261132` (`N = 6` paired seeds × `2` conditions × `3` arms = `36 / 36` succeeded runs, `failed_run_count = 0`, `2269.22 s` total wall time, exact paired sign-flip test `2^6 = 64` permutations, minimum `p = 0.03125`) under `mesoln_40hz_acute_edge_mask` vs. `mesoln_40hz_baseline`:

| Arm & Protocol | Model / Parameter Change | Wall Time | Neuron `523539` Base -> Mask (Δ, 95% CI, Exact `p`) | Neuron `558778` Base -> Mask (Δ, Exact `p`) | Neuron `10592` Base -> Mask (Δ, Exact `p`) |
|---|---|---:|---|---|---|
| `shiu_lif` ([`P5-PAIN-001-ROBUST-SHIU-LIF.yaml`](../../protocols/P5-PAIN-001-robust-shiu-lif.yaml), `6f56bd5a...`) | `shiu2024_lif` (`linear` solver, `dg_unless_refractory: true`, manifest `12bc0160...`) | `808.73 s` | `14.375 -> 31.458 Hz` (`+17.083 ± 2.041`, `[15.625, 18.542]`, `p = 0.03125`) | `14.792 -> 18.542 Hz` (`+3.750`, `p = 0.03125`) | `10.833 -> 14.375 Hz` (`+3.542`, `p = 0.03125`) |
| `wsyn_low` ([`P5-PAIN-001-ROBUST-WSYN-LOW.yaml`](../../protocols/P5-PAIN-001-robust-wsyn-low.yaml), `8e56e515...`) | `synapse_lif_v1`, `w_syn_v = 0.2475 mV` (-10%, manifest `f0067f48...`) | `729.21 s` | `12.083 -> 32.917 Hz` (`+20.833 ± 2.582`, `[18.958, 22.708]`, `p = 0.03125`) | `16.875 -> 19.583 Hz` (`+2.708`, `p = 0.03125`) | `11.875 -> 14.167 Hz` (`+2.292`, `p = 0.03125`) |
| `wsyn_high` ([`P5-PAIN-001-ROBUST-WSYN-HIGH.yaml`](../../protocols/P5-PAIN-001-robust-wsyn-high.yaml), `d52411e3...`) | `synapse_lif_v1`, `w_syn_v = 0.3025 mV` (+10%, manifest `c1e05e03...`) | `729.80 s` | `7.500 -> 22.708 Hz` (`+15.208 ± 5.938`, `[10.000, 18.750]`, `p = 0.03125`) | `10.208 -> 13.125 Hz` (`+2.917`, `p = 0.03125`) | `6.667 -> 7.500 Hz` (`+0.833`, `p = 0.25`) |

- **`w_syn_v` Sensitivity Summary (`0.2475 -> 0.275 -> 0.3025 mV`):** Stronger global synaptic scaling monotonically reduced baseline firing on both primary readouts (`523539`: `12.083 -> 11.917 -> 7.500 Hz`, range `4.583 Hz`, `monotone_decreasing`; `558778`: `16.875 -> 13.500 -> 10.208 Hz`, range `6.667 Hz`, `monotone_decreasing`), reflecting stronger recruited feedforward inhibition. Across all three structural/parametric arms, pathway-selective `acute_edge_mask` amplification remained positive on `523539` (`+15.208` to `+20.833 Hz`, `p = 0.03125` everywhere) and `558778` (`+2.708` to `+3.833 Hz`, `p = 0.03125`).

---

## 7. Local Archival Bundles & Scientific Scope Limits

Six reproducible local bundles were exported under `runs/phase5_pain001_confirmatory/` (`bundle_523539_edge_mask`, `bundle_523539_edge_mask_spec`, `bundle_523539_cell_death`, `bundle_523539_cell_death_spec`, `bundle_558778_edge_mask`, `bundle_558778_edge_mask_spec`), each containing `REPRODUCIBILITY.md`, provenance manifests, summary JSON, and SVG/PNG firing-rate figures (excluded from Git per `runs/` gitignore rule).

### Mandatory Limitations & Non-Claims

1. **Single-Specimen Structural Constraint:** `malecns_v1_0` represents one adult male *Drosophila* CNS reconstruction; it cannot establish population variance or male-vs-female dimorphism.
2. **L1 LIF Biophysical Simplifications:** `synapse_lif_v1` assigns uniform `w_syn_v`, uniform delay (`1.8 ms`), and single-sign neurotransmitter predictions (`GABA`, `acetylcholine`, `glutamate`) without `GABA_A`/`GABA_B` receptor kinetics, metabotropic modulation, extrasynaptic peptides, or intrinsic persistent currents — explaining why post-stimulus firing decayed within `~10 ms`.
3. **Acute Circuit Disinhibition vs. Chronic Pain Remodeling:** Neither `EdgeMaskModulation` nor `NeuronSilencing` models weeks-long post-injury transcriptional reprogramming, structural sprouting, or mammalian dorsal-horn microglia/astrocyte signaling.
4. **Literature Provenance Discipline:** While `Khuong et al. 2019` and `Cheong et al. 2026` provide peer-reviewed adult VNC sensory/premotor framing, `Jones et al. 2025` remains tracked explicitly in [`evidence_register.md`](evidence_register.md) as a non-peer-reviewed bioRxiv preprint.
5. **Cross-References:** Exploratory context in [`pilot_report.md`](pilot_report.md), [`model_card.md`](model_card.md), and [`ADR-0006`](../../../docs/adr/ADR-0006-phase5-pain-vnc-disinhibition.md).
