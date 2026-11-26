# Phase 5C-3 Stress L3 Verification & L1 Pilot Report (`P5-STRESS-001-PILOT`, RUO)

> Status: Exploratory pilot complete (`24/24` runs); confirmatory `P5-STRESS-001.yaml` remains an unfrozen draft pending human review.  
> Specimen & Model: Adult male `malecns_v1_0` (`211,577` neurons, `26,028,386` edges) + `stress_allostatic_reactive_scope_v1` (L3) -> `synapse_lif_v1` (L1).  
> Run Provenance: `job_db4f5c45ac4e`, `24/24` succeeded (`failed_run_count = 0`), `sham_max_spikes = 0` (`sham_count = 3`), summed worker CPU wall `3918.05 s` (`run_wall_mean_s = 163.25 s`), commit `ce513da`.

## 1. L3 Reactive-Scope Allostatic ODE Verification (`5/5` Gates)

- `rk45_convergence_and_bounds`: **PASS** (`max_step 0.05 h` vs `0.01 h` `max_abs_diff = 1.184e-05`, bounds preserved).
- `sham_baseline_invariance`: **PASS** (`sham_max_a = 0.0`, `sham_max_c_dev = 0.0`, `sham_max_l = 0.0`).
- `acute_stress_habituation_and_recovery`: **PASS** (`a_peak = 0.402`, `c_min = 0.969`, `a_end = 1.19e-132`).
- `chronic_allostatic_overload_separation`: **PASS** (`c_min = 0.497`, `l_peak = 1.792`, `80.21x` acute load ratio, late bout `a_peak = 0.524 > 0.430`).
- `post_chronic_washout_and_ruo_guard`: **PASS** (`c` recovers `0.545 -> 0.934`, `l` drops `0.978 -> 0.318`, `diagnostic_label_guard_enabled = True`).

## 2. L1 MaleCNS Pilot Readout Cohort Means (`N=3` paired seeds, `0.0–0.6 s`)

| Condition | `DNp01` Escape (`10001/10010`, Hz) | `DNp09` Freeze (`11177/10783`, Hz) | `DNp11` Escape (`10106/10259`, Hz) |
|---|---|---|---|
| `sham_zero_stimulus` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000 ± 0.000` |
| `acute_threat_baseline_30hz` | `12.222 ± 5.092` | `13.056 ± 0.962` | `8.056 ± 2.097` |
| `acute_threat_high_60hz` | `19.722 ± 8.430` | `20.556 ± 3.155` | `21.944 ± 2.097` |
| `chronic_allostatic_reserve_drop` (`0.5x` gate) | `46.667 ± 7.638` | `10.556 ± 0.481` | `21.111 ± 3.469` |
| `chronic_allostatic_reserve_depletion` (`0.0x` mask) | `57.500 ± 8.036` | `20.278 ± 4.883` | `20.278 ± 2.927` |
| `chronic_arousal_sensory_sensitization` (`1.4x + 0.5x`) | `63.056 ± 3.469` | `16.667 ± 1.443` | `31.667 ± 1.443` |
| `matched_ctrl_nondefensive_visual_60hz` | `29.444 ± 6.736` | `0.000 ± 0.000` | `4.444 ± 1.273` |
| `matched_ctrl_offpathway_inh_depletion` | `12.500 ± 0.000` | `12.778 ± 1.735` | `7.778 ± 1.925` |

## 3. Specificity Controls & Honest Nuance Findings

- **Inhibitory Reserve Erosion Specificity:** Removing `100%` of the defensive `30`-cell `GABA`/`GLUT` gate onto `DNp01/DNp09` sharply increased `DNp01_R` (`10001`: `+15.556 Hz`, CI `[11.667, 18.333]`), `DNp01_L` (`10010`: `+75.000 Hz`, CI `[65.000, 81.667]`), `DNp09_R` (`11177`: `+3.333 Hz`), and `DNp09_L` (`10783`: `+11.111 Hz`), whereas deleting `30` Hungarian-matched off-pathway `GABA`/`GLUT` neurons (`max|SMD|=0.1279`) left firing at baseline (`10001`: `+0.556 Hz`, CI `[-6.667, 8.333]`; `11177`: `+0.556 Hz`, CI `[0.000, 1.667]`).
- **Honest Non-Defensive Visual Spillover Finding:** Although `matched_lc12_visual_controls` (`max|SMD|=0.0676`) had **zero direct 1-hop synapses** onto `DNp01/09/11` and produced **`0.000 Hz`** on `DNp09` freezing (`vs 20.556 Hz` in `acute_threat_high_60hz`), `60 Hz` stimulation still recruited Giant Fiber `DNp01` (`29.444 Hz`, `10001` `+6.111 Hz` over `acute_60hz`) through `>=2`-hop polysynaptic visual premotor relays. For confirmatory freezing specificity, `DNp09` cleanly isolates direct `LC9` drive while multi-hop `>=2`-hop exclusion should be applied if strict visual negative control is required on `DNp01`.
- **Evidence Bundles Exported:** `bundle_10001_reserve_depletion_vs_acute`, `bundle_11177_reserve_depletion_vs_acute`, and `bundle_10001_sensitized_vs_acute` under `runs/phase5c_stress001_exploratory_pilot/`.
- **Wall-Time Estimate for Confirmatory (`N=15`, `120` runs):** `40` batches at `workers=3` × `163.25 s` mean run wall ≈ `1.81 h` CPU wall time.
