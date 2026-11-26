# Phase 5C-2 Pharma L2 Verification & L1 Pilot Report (`P5-PHARMA-001-PILOT`, RUO)

> Status: Exploratory pilot complete (`24/24` runs); confirmatory `P5-PHARMA-001.yaml` remains an unfrozen draft pending human review.  
> Specimen & Model: Adult male `malecns_v1_0` (`211,577` neurons, `26,028,386` edges) + `receptor_conductance_modulation_v1` (L2) -> `synapse_lif_v1` (L1).  
> Run Provenance: `job_c1738acea7b9`, `24/24` succeeded (`failed_run_count = 0`), `sham_max_spikes = 0` (`sham_count = 3`), summed worker CPU wall `3329.3 s` (`run_wall_mean_s = 138.72 s`), commit `5f807ef`.

## 1. L2 Dose-Independent Kinetics Verification (`5/5` Gates)

- `hill_boundary_and_half_max`: **PASS** (`E(0)=0`, `E(1)=0.5`, `E(1e6)>0.999999` for `n in {1.0, 1.3, 1.6}`).
- `schild_linearity_and_slope`: **PASS** (root-solved Schild slope `1.000000`, $R^2 = 1.0$, max dose-ratio error `7.11e-15`).
- `noncompetitive_vs_pam_directionality`: **PASS** (`Rdl` antagonist strictly decreasing `1.0 -> 0.0`, half-point `0.5` at `[I]/IC50=1`; `Rdl` PAM strictly increasing `1.0 -> 2.0`, half-point `1.5` at `[M]/Km=1`; pilot `1.75x` mapped to `[M]/Km = 2.4980`).
- `bliss_independence_identity`: **PASS** (`(0.5, 0.5) -> 0.75`, `(0.3, 0.4) -> 0.58`).
- `ruo_dose_independent_guard`: **PASS** (`named_compound_gate_enabled = False`, dimensionless affinity ratios only).

## 2. L1 MaleCNS Pilot Readout Means (`N=3` paired seeds, `0.0–0.6 s`)

| Condition | `523539` (`ANXXX027_L`, Hz) | `558778` (`AN08B012_R`, Hz) | `10592` (`AN08B012_L`, Hz) |
|---|---|---|---|
| `sham_zero_stimulus` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000 ± 0.000` |
| `vehicle_baseline_40hz` | `14.444 ± 0.962` | `15.556 ± 0.962` | `10.000 ± 2.887` |
| `rdl_gaba_antag_50pct` | `19.444 ± 0.962` (`+5.000`) | `15.000 ± 1.667` | `8.889 ± 0.962` |
| `rdl_gaba_antag_100pct` | `35.556 ± 0.962` (`+21.111`) | `19.444 ± 0.962` (`+3.889`) | `13.333 ± 0.000` (`+3.333`) |
| `rdl_gaba_pam_175pct` | `9.444 ± 2.546` (`-5.000`) | `12.778 ± 0.962` (`-2.778`) | `8.333 ± 1.667` (`-1.667`) |
| `nachr_ach_atten_50pct` | `6.667 ± 4.410` (`-7.778`) | `7.778 ± 2.546` (`-7.778`) | `3.889 ± 0.962` (`-6.111`) |
| `combined_rdl_pam_plus_nachr_atten` | `3.333 ± 0.000` (`-11.111`) | `6.111 ± 2.546` (`-9.444`) | `2.222 ± 0.962` (`-7.778`) |
| `matched_ctrl_rdl_antag_100pct` | `13.889 ± 3.469` (`-0.556`) | `15.556 ± 1.925` (`+0.000`) | `10.000 ± 0.000` |

## 3. Bliss Independence & Control Specificity Observations

- **`523539` (`ANXXX027_L`):** `rdl_gaba_pam_175pct` suppressed firing by `34.62%` and `nachr_ach_atten_50pct` by `53.85%`. Their Bliss independence null expectation is `0.3462 + 0.5385 - (0.3462 * 0.5385) = 0.6982` (`69.82%`); observed combined suppression (`3.333 Hz` vs `14.444 Hz` vehicle) reached `0.7692` (`76.92%`, excess `+0.0710`).
- **`558778` (`AN08B012_R`):** Single-arm suppressions (`0.1786` PAM, `0.5000` nAChR) predict Bliss null `0.5893` vs. observed combined suppression `0.6071` (excess `+0.0179`, near-Bliss additivity).
- **Matched Off-Pathway Control:** Blocking `100%` of outgoing GABA synapses on `matched_vnc_gaba_controls` (`26` neurons, `15,854` outgoing edges, `0` to ascending readouts) shifted `523539` by `-0.556 Hz` (`95% CI [-3.333, 1.667]`) and `558778` by `+0.000 Hz` (`[-1.667, 1.667]`).
- **Evidence Bundles Exported:** `bundle_523539_rdl_antag100_vs_veh`, `bundle_523539_rdl_pam_vs_veh`, and `bundle_523539_combined_vs_veh` under `runs/phase5c_pharma001_exploratory_pilot/`.
- **Wall-Time Estimate for Confirmatory (`N=15`, `120` runs):** `40` batches at `workers=3` × `138.72 s` mean run wall ≈ `1.54 h` CPU wall time.
