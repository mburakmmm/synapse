# Exploratory Pilot Report: `P5-PAIN-001-PILOT` (NOT Confirmatory)

> **EXPLORATORY PILOT ONLY (`analysis_intent: exploratory`, `status: draft`, `N = 3` paired seeds):** Executed on full `malecns_v1_0` strictly to calibrate tactile stimulation range (`20 Hz` vs. `40 Hz`), contrast acute `edge_mask` vs. partial attenuation vs. full GABA silencing, and budget compute prior to human review of [`P5-PAIN-001.yaml`](../../protocols/P5-PAIN-001.yaml). **Not** confirmatory evidence or wet-lab biological validation (`RUO`).

## 1. Provenance & Execution Accounting

- **Dataset:** `malecns_v1_0` (`v1.0`, `malecns_male_01`, `211,577` bodies, `26,028,386` edges; manifest `6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`, graph `ef5324051bbaaf960cc12754f1017b14700dc725c2c85e5afce75fb5a45256ce`).
- **Pilot Protocol:** [`P5-PAIN-001-pilot.yaml`](../../protocols/P5-PAIN-001-pilot.yaml) (`protocol_sha256: 4938436d7f1a63b2588a48ccbf038927246273cdea3dcca0a43cb269cb1ca8c2`, `master: 20261130`, `replicates: 3`, `duration: 0.8 s`, `synapse_lif_v1`).
- **Target & Control Artifact:** [`pain001_malecns_v1_targets.json`](target_sets/pain001_malecns_v1_targets.json) (`30` `R-MesoLN` afferents; `26` feedforward VNC `GABA` targets vs. `26` matched VNC `GABA` controls; `out_degree smd = -0.0196`, `out_synapses smd = +0.0310`, `in_degree smd = -0.0970`, `in_synapses smd = -0.0082`; `0` direct control edges to ascending relays).
- **Run Completeness (`runs/phase5_pain001_exploratory_pilot/`):** `24/24` succeeded (`failed_run_count = 0`), `sham_zero_stimulus max_total_spikes = 0` (`3/3`), total wall `1507.23 s` (`~25.12 min` with `--workers 3`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`), per-run wall `176.66–195.23 s` (mean `184.36 s`).

## 2. Windowed Stimulus (`0.1–0.6 s`) & Post-Stimulus Persistence (`0.6–0.8 s`) Means (`N = 3`)

All conditions yielded `pre_rate_hz = 0.000 ± 0.000 Hz` (`[0.0, 0.1) s`) and `sham_zero_stimulus = 0.000 ± 0.000 Hz` across all `8` monitored neurons. Remaining silent relays (`13166 AN08B012_R`, `14994 ANXXX027_R`, `800146 TTMn_R`) stayed `0.000 Hz` during `[0.1, 0.6) s` across all arms (`800146` fired `1` late spike in 1/3 `acute_edge_mask` replicates: `post = 1.667 Hz`).

| Condition | `523539` (`ANXXX027_L`) Stim ± SD (Hz) | `558778` (`AN08B012_R`) Stim ± SD (Hz) | `10592` (`AN08B012_L`) Stim ± SD (Hz) | `804642` (`TTMn_L`) Stim (Hz) | Post Persistence `523539`/`558778` (ms) |
|---|---:|---:|---:|---:|---:|
| `sham_zero_stimulus` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000` | `0.00` / `0.00` |
| `mesoln_20hz_baseline` | `10.000 ± 2.000` | `7.333 ± 1.155` | `6.000 ± 2.000` | `0.667` | `0.93` / `0.00` |
| `mesoln_20hz_gaba_cell_death` | `18.667 ± 1.155` | `12.000 ± 2.000` | `4.667 ± 1.155` | `0.667` | `0.00` / `0.00` |
| `mesoln_40hz_baseline` | `18.000 ± 3.464` | `20.667 ± 1.155` | `15.333 ± 1.155` | `0.667` | `0.40` / `1.27` |
| `mesoln_40hz_matched_ctrl_ablation` | `16.667 ± 4.619` | `19.333 ± 2.309` | `13.333 ± 2.309` | `0.667` | `1.27` / `0.93` |
| `mesoln_40hz_gaba_atten_50pct` | `30.000 ± 2.000` | `22.667 ± 1.155` | `15.333 ± 2.309` | `0.667` | `0.00` / `0.00` |
| `mesoln_40hz_gaba_cell_death` | `43.333 ± 5.033` | `20.667 ± 1.155` | `9.333 ± 1.155` | `2.667` | `0.47` / `0.23` |
| `mesoln_40hz_acute_edge_mask` | `51.333 ± 1.155` | `28.000 ± 3.464` | `17.333 ± 1.155` | `0.667` | `0.53` / `0.00` |

## 3. Full-Trial (`0.0–0.8 s`) Paired Contrasts & Sensitivity (`N = 3`)

Notice exact `N = 3` (`2^3 = 8`) exact permutation floor yields minimum `p = 0.250` regardless of effect separation (`q >= 0.2917`).

| Target Relay | Contrast | Base -> Trt Mean (Hz) | Paired Δ ± SD (Hz) | 95% Bootstrap CI (Hz) | Exact `p` / BH-FDR `q` |
|---|---|---:|---:|---|---:|
| `523539` (`ANXXX027_L`) | `40hz_cell_death - baseline` | `11.667 -> 27.500` | `+15.833 ± 1.443` | `[+15.000, +17.500]` | `0.2500` / `0.2917` |
| `523539` (`ANXXX027_L`) | `40hz_acute_edge_mask - baseline` | `11.667 -> 32.500` | `+20.833 ± 1.443` | `[+20.000, +22.500]` | `0.2500` / `0.2917` |
| `523539` (`ANXXX027_L`) | `40hz_atten50 - baseline` | `11.667 -> 18.750` | `+7.083 ± 1.909` | `[+5.000, +8.750]` | `0.2500` / `0.2917` |
| `523539` (`ANXXX027_L`) | `40hz_cell_death - matched_ctrl` | `10.833 -> 27.500` | `+16.667 ± 1.909` | `[+15.000, +18.750]` | `0.2500` / `0.2917` |
| `523539` (`ANXXX027_L`) | `40hz_matched_ctrl - baseline` | `11.667 -> 10.833` | `-0.833 ± 3.146` | `[-3.750, +2.500]` | `0.7500` / `0.7500` |
| `523539` (`ANXXX027_L`) | `20hz_cell_death - baseline` | `6.667 -> 11.667` | `+5.000 ± 2.165` | `[+3.750, +7.500]` | `0.2500` / `0.2917` |
| `558778` (`AN08B012_R`) | `40hz_acute_edge_mask - baseline` | `13.333 -> 17.500` | `+4.167 ± 2.602` | `[+1.250, +6.250]` | `0.2500` / `0.8750` |
| `558778` (`AN08B012_R`) | `40hz_cell_death - baseline` | `13.333 -> 13.333` | `0.000 ± 1.250` | `[-1.250, +1.250]` | `1.0000` / `1.0000` |
| `558778` (`AN08B012_R`) | `20hz_cell_death - baseline` | `4.583 -> 7.500` | `+2.917 ± 0.722` | `[+2.500, +3.750]` | `0.2500` / `0.8750` |
| `10592` (`AN08B012_L`) | `40hz_acute_edge_mask - baseline` | `9.583 -> 10.833` | `+1.250 ± 0.000` | `[+1.250, +1.250]` | `0.2500` / `0.4375` |
| `10592` (`AN08B012_L`) | `40hz_cell_death - baseline` | `9.583 -> 5.833` | `-3.750 ± 1.250` | `[-5.000, -2.500]` | `0.2500` / `0.4375` |

## 4. Scientific Takeaways & Confirmatory Design Justification

1. **Disinhibition vs. Cell-Death Separation:** Cutting *only* direct `GABA -> ascending` synapses (`acute_edge_mask`) amplifies all three active ipsilateral/contralateral relays (`523539`, `558778`, `10592`), whereas global `both_zero` silencing (`gaba_cell_death`) yields a strong `+15.833 Hz` boost (`stim: 18.0 -> 43.3 Hz`) on `523539` (`ANXXX027_L`) while sparing `558778` and reducing `10592` (`-3.750 Hz`)—reflecting intra-VNC recurrent redistribution when GABA cells themselves lose incoming inhibition.
2. **Low-Drive Sensitivity (`20 Hz`):** At `20 Hz`, `gaba_cell_death` raises `523539` (`10.0 -> 18.7 Hz`) and `558778` (`7.3 -> 12.0 Hz`) to levels comparable to uninjured `40 Hz` baseline (`18.0` / `20.7 Hz`), modeling an acute threshold-lowering analog without claiming chronic plasticity.
3. **Rapid Post-Stimulus Decay (`<= 1.3 ms`):** Absence of sustained post-stimulus firing reflects pure L1 LIF time constants (`5–20 ms`) without neuromodulatory feedback loops.
4. **Compute Budget for `P5-PAIN-001.yaml`:** With mean `~184 s/run` (`~63 s` effective wall time/run at `--workers 3`), `8` conditions × `N = 15` replicates = `120` runs (~`2.1 hours`) provides exact-resolution Monte Carlo permutation tests (`10,000` draws -> `p >= 9.999e-05`) within local workstation bounds.
