# Exploratory Report: `addiction` Module (`L2 Plasticity` + `P5-ADD-001-PILOT`)

> **Research Use Only (RUO):** Documents Stage 1 L2 three-factor MB plasticity verification (`5/5` gates) and Stage 2 L1 whole-CNS exploratory simulation (`N = 3`, `24/24` runs) on `malecns_v1_0`. All outcomes are *Drosophila* cue-conditioning proxies, **not** human clinical addiction or dependence (`AGENTS.md` §1, §8, §10). Confirmatory [`P5-ADD-001.yaml`](../../protocols/P5-ADD-001.yaml) remains `status: draft`.

## 1. Stage 1 — L2 MB Plasticity Gates & Control Arms (`mb_dopamine_plasticity_v1`)

- **Model Manifest:** `mb_dopamine_plasticity_v1` (`sha256: ca302818cd9281529831192317dc78131b537327a398fad1c64c02fef8c402b4`), artifacts in gitignored `runs/phase5b_add001_l2_plasticity/` (`l2_verification_gate.json`, `l2_paradigm_summary.json`, `l2_timeseries.parquet`, `figures/`).

| Verification Gate | Measured Value | Acceptance Criterion | Status |
|---|---|---|---|
| **RK4 Convergence & Bounds** | `dt=0.05 s` vs `0.025 s`: `max|dW|=1.9469e-4`, `max|dPI|=7.855e-5`, bounds `[0.15, 1.0]` | `max|dW| < 1e-3`, `max|dPI| < 1e-3`, weights finite in `[w_min, w_max]` | **PASS** |
| **CS+ Acquisition Specificity** | `PI_acq = +0.33123`, `w_avoid(CS+) = 0.292978`, `|w_avoid(CS-) - 1.0| = 0.0` | `PI_acq >= 0.30`, `w_avoid <= 0.55`, `|w_avoid(CS-) - 1.0| < 1e-6` | **PASS** |
| **Parallel-Memory Extinction** | `PI_ext = +0.045171` (`drop = 0.286059`), `w_appr = 0.384344`, `w_avoid = 0.334152` | `PI_ext <= 0.15`, `drop >= 0.25`, `w_appr <= 0.55`, `w_avoid <= 0.65` | **PASS** |
| **Reinstatement Recovery** | `PI_reinst = +0.26580` (`gain = +0.220629`), `w_appr = 0.924609`, `|w_avoid(CS-) - 1| = 0.0` | `gain >= 0.15`, `PI_reinst >= 0.25`, `|w_avoid(CS-) - 1.0| < 1e-6` | **PASS** |
| **Negative Controls Nullity** | `sham = 0.0` (`dev=0.0`), `yoked_acq = +6.2e-5`, `dan_blocked = 0.0` | `sham < 1e-9`, `|yoked_acq| < 0.05`, `dan_blocked < 1e-9` | **PASS** |
| **Spontaneous Recovery Comparison** | Passive retention (`310 s`, no PAM): `PI = +0.1648` (`w_appr = 0.6266`) vs. `+0.2658` | Reward re-exposure exceeds passive spontaneous recovery | **PASS** |

## 2. Stage 2 — L1 Whole-CNS Exploratory Pilot (`P5-ADD-001-PILOT`, `24/24` runs)

- **Execution:** `24/24` runs succeeded (`failed_run_count = 0`, `sham_max_spikes = 0`, sum of per-run wall times `3464.20 s`, wall time ~`19.9 min` on 3 workers; per-run `min = 136.29 s`, `mean = 144.34 s`, `max = 163.07 s`), protocol `sha256: 5151305f6d165a8a0eba08e51fe81664bf2ec75b17d5347b80e7cd79809e5da9`.
- **Two-Window Mechanistic Signature in Full-CNS (`211,577` nodes):**
  - **Early Feedforward Onset (`[0.1, 0.2) s`):** Before polysynaptic reverberation recruits extraprotocerebral loops, `MBON02_L` (`522749`) fired at `26.67 Hz` in naive & `matched_ctrl`, dropped to **`0.00 Hz`** upon `cs_plus_post_acquisition`, while `MBON14` averaged `16.67 -> 19.17 Hz` (acq) `-> 0.00 Hz` (ext) `-> 15.83 Hz` (reinst), driving early L1 valence from `-0.0959` (`naive` / `matched_ctrl`) to `+1.0000` (`acq`) `-> 0.0000` (`ext`) `-> +1.0000` (`reinst`), while `CS-` held at `-0.6034` identically.
  - **Full Stimulus Window (`[0.1, 0.6) s`) & Recurrent Loop Ignition:** Sustained `35 Hz` `CS+` KC drive crossed the `MBON12/14/18 -> CRE011/SMP/LH -> KCab` recurrent threshold (`11,985–12,274` active neurons across CNS in `[0.2, 0.6] s`; `2/3` naive seeds ignited, `3/3` acq/reinst seeds ignited, `2/3` ext seeds quenched), driving strong approach-MBON modulation (`MBON14`: `180.33 -> 257.66 -> 49.50 -> 243.17 Hz`) alongside late recurrent drive back onto `MBON02` (`197.33 -> 270.67 -> 55.33 -> 257.33 Hz`). `MBON04` (`525780`, `530875`) stayed `0.00 Hz` across all conditions.

### Exploratory Full-Trial (`0.0–0.6 s`) Paired Contrasts (`N = 3`)

| Neuron (`Cell Type`) | Comparison | Base Mean ± SD (Hz) | Treat Mean ± SD (Hz) | Paired Δ ± SD (Hz) | Bootstrap 95% CI |
|---|---|---|---|---|---|
| `17946` (`MBON14_R`) | `post_acquisition` vs. `naive_baseline` | `167.222 ± 113.582` | `238.333 ± 10.408` | **`+71.111 ± 115.954`** | `[+3.333, +205.000]` |
| `522749` (`MBON02_L`) | `post_acquisition` vs. `naive_baseline` (full-trial incl. `[0.2,0.6]s` feedback) | `169.444 ± 109.599` | `225.556 ± 6.736` | **`+56.111 ± 110.206`** | `[-10.000, +183.333]` |
| `17946` (`MBON14_R`) | `post_extinction` vs. `post_acquisition` | `238.333 ± 10.408` | `45.000 ± 77.942` | **`-193.333 ± 75.719`** | `[-246.667, -106.667]` |
| `14221` (`MBON18_R`) | `post_extinction` vs. `post_acquisition` | `215.556 ± 11.097` | `39.444 ± 68.320` | **`-176.111 ± 66.798`** | `[-225.000, -100.000]` |
| `13728` (`MBON12_L`) | `post_extinction` vs. `post_acquisition` | `218.333 ± 5.000` | `43.889 ± 76.018` | **`-174.444 ± 76.182`** | `[-223.333, -86.667]` |
| `17946` (`MBON14_R`) | `post_reinstatement` vs. `post_extinction` | `45.000 ± 77.942` | `223.889 ± 6.736` | **`+178.889 ± 71.207`** | `[+96.667, +220.000]` |
| `14221` (`MBON18_R`) | `post_reinstatement` vs. `post_extinction` | `39.444 ± 68.320` | `201.667 ± 7.265` | **`+162.222 ± 61.109`** | `[+91.667, +198.333]` |
| `17946` (`MBON14_R`) | `yoked_matched_ctrl` vs. `naive_baseline` | `167.222 ± 113.582` | `166.667 ± 113.186` | **`-0.556 ± 0.962`** | `[-1.667, 0.000]` |
| `522749` (`MBON02_L`) | `cs_minus_after_acq` vs. `cs_minus_naive` | `54.444 ± 0.962` | `54.444 ± 0.962` | **`+0.000 ± 0.000`** | `[0.000, 0.000]` |

## 3. Draft Confirmatory Recommendation (`P5-ADD-001.yaml`)

- Draft [`P5-ADD-001.yaml`](../../protocols/P5-ADD-001.yaml) (`status: draft`, `N = 15`, `master = 20261151`, `120` runs, estimated `~1.60 h` at `workers = 3`, `sha256: cd975c1a97e62ed10079902a8c7629ddb877dc7344bf88c75cddbc0293260811`) predeclares 6 BH-FDR primary contrasts across `MBON14_R` (`17946`), `MBON18_R` (`14221`), and `MBON12_L` (`13728`) plus secondary `[0.1, 0.2) s` `MBON02_L` (`522749`), yoked matched control, and `CS-` specificity endpoints. Do **not** freeze or run without explicit human approval.
