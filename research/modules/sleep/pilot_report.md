# Exploratory Report: `sleep` Module (`L3 Oscillator` + `P5-SLEEP-001-PILOT`)

> **Research Use Only (RUO):** Documents Stage 1 L3 circadian-homeostatic verification + shift-work dynamics and Stage 2 L1 whole-CNS exploratory simulation (`N = 3`, `24/24` runs) on `malecns_v1_0`. All outcomes remain conditional on differential-equation and L1 LIF assumptions; confirmatory `P5-SLEEP-001.yaml` remains `status: draft` (`AGENTS.md` §8, §10).

## 1. Stage 1 — L3 Circadian-Homeostatic Verification Gates & Shift-Work Results

- **Model Manifest:** `leloup_goldbeter_1998_two_process_v1` (`sha256: 348fc343c91a2d709bbda918492dc5a52a7758be1f8f350fd01d0dd1f0622c23`), artifacts in gitignored `runs/phase5b_sleep001_l3_oscillator/` (`l3_verification_gate.json`, `l3_shift_work_summary.json`, `l3_timeseries.parquet`, `figures/`).

| Verification Gate | Measured Value | Acceptance Criterion | Status |
|---|---|---|---|
| **DD Free-Running & Convergence** | `tau_DD = 24.1346 h` (SD `1e-05 h`), fine-step `24.1346 h` (`diff = 0.0 h`) | `23.5 <= tau <= 24.8 h`, `SD < 0.05 h`, `conv < 0.05 h` | **PASS** |
| **LD 12:12 Entrainment (`t >= 192 h`)** | `tau_LD = 24.0171 h`, `ZT_peak = 21.4539 ± 0.0295 h` | `|tau - 24.0| <= 0.10 h`, `ZT SD < 0.10 h` | **PASS** |
| **2 h Light-Pulse PRC** | Day dead zone `|shift| <= 0.0035 h` (`CT 3–9`); `CT 15 = -2.3591 h`; `CT 21 = +2.3431 h` | `CT3–9 |shift| < 0.35 h`; `min <= -0.50 h`; `CT21 > +1.00 h` | **PASS** |
| **12 h Forced-Wake Rebound** | `S_peak`: `0.9283` vs. `0.7425`; `[168, 192)` rest rebound `+0.1625`; Day-9 washout `-0.0042` | `dep S > +0.10`; rebound `> +0.08`; `|washout| < 0.03` | **PASS** |
| **Negative Control (`v_dT_light = 2.0`)** | Fails LD/PRC gates and raises `RuntimeError` blocking shift-work execution | Must fail-closed when light input disabled | **PASS** |

### Gated 16-Day (`384 h`) Shift-Work Dynamics

| Schedule Arm | Max `|Phase Error|` (h) | Re-entrainment Days | Peak `S` | Mean Post-Onset Rest Fraction |
|---|---|---|---|---|
| `ld12_12_control` | `0.181 h` | `0.886 d` | `0.7434` | `0.5032` |
| `deprivation_12h_recovery` | `0.181 h` | `0.886 d` | `0.9283` | `0.4814` (`+0.1625` in `24 h` post) |
| `shift_delay_8h` (`+8 h` at `t=144 h`) | `5.793 h` | `2.206 d` | `0.7431` | `0.5016` |
| `shift_advance_6h` (`-6 h` at `t=144 h`) | `7.303 h` | `2.641 d` | `0.7541` | `0.5032` |
| `rotating_shift_8h` (3-day cycles) | `10.814 h` | `None` (never stably re-entrains) | `0.7419` | `0.4991` |

## 2. Stage 2 — L1 Whole-CNS Exploratory Pilot (`P5-SLEEP-001-PILOT`, `24/24` runs)

- **Execution:** `24/24` runs succeeded (`failed_run_count = 0`, `sham_max_spikes = 0`, sum of per-run wall times `4700.87 s`, wall time ~`26.7 min` on 3 workers; per-run `min = 180.16 s`, `mean = 195.87 s`, `max = 217.87 s`), protocol `sha256: e842943affc6fc854b1e5d8353f1b06c99cd9321046af872d8748d182c619715`.
- **Cohort Stimulus-Window (`[0.1, 0.6) s`) Mean Firing Rates (Hz):**
  - `tutub_b_interneuron` (`2` `GLUT`): `160.33 Hz` (`light_day_baseline`) -> **`141.67 Hz`** (`+clock_dn1p_drive`) vs. `162.00 Hz` (`+matched_ctrl_clock_drive`) -> rescued to **`162.00 Hz`** (`+dn1p_avp_edge_mask`); jumps to **`199.00 Hz`** (`shift_light_misaligned_clock_debt`).
  - `tubu01_relay` (`10` `ACH`): `2.07 Hz` (`baseline`) -> `1.93 Hz` (`+clock_dn1p_drive`) -> `2.80 Hz` (`+dn1p_avp_edge_mask`) -> **`9.87 Hz`** (`shift_light_misaligned_clock_debt`).
  - `exr1_helicon` (`4` `ACH`) & `er5_sleep_homeostat` (`21` `GABA`): remain sub-threshold (`0.00 Hz`) across `30 Hz` `MeTu2a` conditions (hence `er5_high_homeostat_gain` and `er5_exr1_edge_mask` produce `0.00 Hz` difference at `30 Hz`), then cross threshold together under `50 Hz` misaligned light + debt (`ExR1 = 3.83 Hz`, `ER5 = 2.83 Hz`, `EPG = 0.01 Hz`).

### Exploratory Full-Trial (`0.0–0.8 s`) Paired Contrasts (`N = 3`)

| Neuron (`Cell Type`) | Comparison | Base Mean ± SD (Hz) | Treat Mean ± SD (Hz) | Paired Δ (Hz) | Bootstrap 95% CI |
|---|---|---|---|---|---|
| `22794` (`TuTuB_b_R`) | `clock_dn1p_drive` vs. `light_day_baseline` | `102.083 ± 2.602` | `89.167 ± 2.602` | **`-12.917`** | `[-18.750, -8.750]` |
| `22794` (`TuTuB_b_R`) | `clock_dn1p_drive` vs. `matched_ctrl_clock_drive` | `101.667 ± 1.443` | `89.167 ± 2.602` | **`-12.500`** | `[-13.750, -11.250]` |
| `22794` (`TuTuB_b_R`) | `dn1p_avp_edge_mask` vs. `clock_dn1p_drive` | `89.167 ± 2.602` | `101.667 ± 1.443` | **`+12.500`** | `[+11.250, +13.750]` |
| `520699` (`TuTuB_b_L`) | `clock_dn1p_drive` vs. `light_day_baseline` | `100.417 ± 1.443` | `89.167 ± 1.909` | **`-11.250`** | `[-13.750, -7.500]` |
| `520699` (`TuTuB_b_L`) | `dn1p_avp_edge_mask` vs. `clock_dn1p_drive` | `89.167 ± 1.909` | `101.250 ± 1.250` | **`+12.083`** | `[+11.250, +12.500]` |
| `114115` (`TuBu01`) | `shift_misaligned` vs. `light_day_baseline` | `4.583 ± 3.146` | `19.167 ± 4.018` | **`+14.583`** | `[+10.000, +18.750]` |
| `11886` (`ExR1`) | `shift_misaligned` vs. `light_day_baseline` | `0.000 ± 0.000` | `2.917 ± 0.722` | **`+2.917`** | `[+2.500, +3.750]` |
| `10043` (`ER5`) | `shift_misaligned` vs. `light_day_baseline` | `0.000 ± 0.000` | `2.083 ± 0.722` | **`+2.083`** | `[+1.250, +2.500]` |

## 3. Draft Confirmatory Recommendation (`P5-SLEEP-001.yaml`)

- Draft [`P5-SLEEP-001.yaml`](../../protocols/P5-SLEEP-001.yaml) (`status: draft`, `N = 15`, `master = 20261141`, `120` runs, estimated `~2.18 h` at `workers = 3`) is prepared with 6 predeclared BH-FDR primary contrasts targeting bilateral `TuTuB_b` (`22794`, `520699`), `TuBu01` (`114115`), and `ExR1` (`11886`), plus secondary `ER5` (`10043`) and `30 Hz` sub-threshold conditions. Do **not** freeze or run without explicit human sign-off.
