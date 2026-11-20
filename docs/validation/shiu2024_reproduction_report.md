# Phase 2 Validation & Reproduction Report: Shiu et al. (2024) Feeding Circuit

> **RESEARCH USE ONLY (RUO):** Conditional on `flywire_fafb_v630` structural graph and the `shiu2024_lif` reduced LIF specification.

## 1. Provenance & Locked Inputs

| Artifact / Field | Identifier / Value | SHA-256 / Hash |
|---|---|---|
| Dataset | `flywire_fafb_v630` (`v630`, `127,400` neurons, `14,687,178` edges, `52,793,639` synapses) | Manifest: `f6965c945c801571371f6f593cdc9d1fc2f6cb8cbe32def898d1640069b4acf9` |
| Normalized Graph | Canonical sparse CSR (`is_synthetic_fixture=false`) | `graph_sha256`: `c8fc14b90aff0200250987dceea9e929129d17c3d09f75354f15251393a00552` |
| Protocol | [`P2-BENCH-SHIU2024`](../../research/protocols/P2-BENCH-SHIU2024.yaml) (`revision: 2`, `analysis_intent: confirmatory`) | `d3ccb47b576c124526c227803deea1d6befe7f1bd830d973ce0cbd17e5f7912c` |
| Model | `shiu2024_lif` (`revision: 1.0`, `brian2_cpu`, `numpy` target, `dt=0.1ms`, `solver=linear`, `dg_unless_refractory=true`) | `12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5` |
| Reference Targets | [`shiu2024_reference_targets.json`](../../research/benchmarks/shiu2024_reference_targets.json) (`SHIU2024-FEEDING-BENCHMARK`) | `a5d8f361d5c21c6c19344f008fd69e20817ddd4c46eb27ff020f42419f86a6f0` |
| Upstream Baseline | `philshiu/Drosophila_brain_model@91bdd1e7dcf193f3e7ca5a8933497fcef63b7960` | `sugarR_100Hz.parquet` (`git-blob-sha1:bd76730d...`), `sugarR-720575940617937543.parquet` (`git-blob-sha1:1cdeee4a...`) |
| Comparison Table | `runs/phase2_shiu2024_reproduction_r2/evaluation/benchmark_comparison.parquet` | `2b4bac372289c5c6fc118457ac817209ccf17402604be505a98ec1f0ad4079bc` |

## 2. Verification & Reproduction Outcomes (`runs/phase2_shiu2024_reproduction_r2`)

- **Run Completeness:** `90/90` runs succeeded (`30` paired replicates × `3` conditions); `failed_run_count = 0`; `overall_passed = true` (`exit_code = 0`).
- **Zero-Stimulus Spike Control (`baseline_no_stimulus`):** `observed_max_total_spikes = 0` (`expected_max_total_spikes = 0`, `passed = true`).

### Predeclared Target Rate Comparisons (`N = 30` replicates per condition)

| Condition | Neuron ID | Label | SYNAPSE Mean ± Pop SD (Hz) | Reference Mean ± Pop SD (Hz) | Signed Δ (Hz) | \|Δ\| (Hz) | Tol (Hz) | Gate |
|---|---|---|---:|---:|---:|---:|---:|---|
| `baseline_no_stimulus` | `720575940660219265` | `MN9_right` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000` | `0.000` | `0.0` | PASS |
| `baseline_no_stimulus` | `720575940645521262` | `MN9_left` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000` | `0.000` | `0.0` | PASS |
| `sugar_grn_100hz` | `720575940660219265` | `MN9_right` | `68.833 ± 4.243` | `67.033 ± 6.595` | `+1.800` | `1.800` | `5.0` | PASS |
| `sugar_grn_100hz` | `720575940645521262` | `MN9_left` | `49.533 ± 4.724` | `48.633 ± 4.672` | `+0.900` | `0.900` | `5.0` | PASS |
| `sugar_grn_100hz` | `720575940622695448` | `top_responder_1` | `114.500 ± 1.962` | `114.267 ± 2.097` | `+0.233` | `0.233` | `5.0` | PASS |
| `sugar_grn_100hz` | `720575940629888530` | `top_responder_2` | `102.667 ± 3.026` | `101.700 ± 3.100` | `+0.967` | `0.967` | `5.0` | PASS |
| `sugar_grn_100hz` | `720575940627383685` | `top_responder_3` | `100.967 ± 1.602` | `101.133 ± 1.875` | `-0.167` | `0.167` | `5.0` | PASS |
| `sugar_grn_100hz_silence_grn15` | `720575940660219265` | `MN9_right` | `63.600 ± 4.432` | `63.267 ± 4.732` | `+0.333` | `0.333` | `5.0` | PASS |
| `sugar_grn_100hz_silence_grn15` | `720575940645521262` | `MN9_left` | `44.933 ± 4.057` | `45.667 ± 4.377` | `-0.733` | `0.733` | `5.0` | PASS |

### Directional Contrast & Paired Statistical Analysis (`MN9_right`, `720575940660219265`)

- **Directional Gate (`grn15_silencing_reduces_mn9_right`):**
  - Contrast: `sugar_grn_100hz_silence_grn15 - sugar_grn_100hz` (`n_pairs = 30`)
  - SYNAPSE mean Δ: `-5.2333 Hz` (SD `6.4897 Hz`) vs reference `-3.7667 Hz` (`expected_direction = negative` -> **PASS**)
- **Paired Seed Ensemble Analysis (`synapse analysis run`, `analysis_mn9`):**
  - Baseline `sugar_grn_100hz`: mean `68.8333 Hz`, sample SD `4.3158 Hz`, median `69.5 Hz`, IQR `4.75 Hz` (`66.25`–`71.0`)
  - Treatment `sugar_grn_100hz_silence_grn15`: mean `63.6000 Hz`, sample SD `4.5075 Hz`, median `63.5 Hz`, IQR `6.50 Hz` (`60.25`–`66.75`)
  - Paired difference mean: `-5.2333 Hz`, 95% percentile bootstrap CI (`n_bootstrap = 2000`, `bootstrap_seed = 0`): `[-7.4342, -2.9658] Hz`, min `-16.0 Hz`, max `10.0 Hz`, `failed_run_count = 0`
  - **Uncertainty Scope:** `conditional_on_model_and_seeds_not_biological_population`
- **Publication Evidence Bundle (`synapse export bundle`, `bundle_mn9`):** Generated cleanly with `REPRODUCIBILITY.md`, provenance manifests, and zero synthetic flags (`is_synthetic_fixture = false`).

## 3. Measured Compute Cost & Audit Trail

- **Hardware / Toolchain:** Windows 11 CPU (`12th Gen Intel(R) Core(TM) i5-12450H`, 8 cores / 12 logical processors, `31.73 GiB` RAM), Python `3.12.11`, `brian2 2.10.1` (`numpy` target; no local C/C++ compiler).
- **Single-Trial Breakdown (`1.0 s` baseline, serial):** `load_graph = 2.73 s`, `build_neu = 0.02 s`, `syn_connect = 0.46 s`, `net_run_1s = 31.28 s` (`31.76 s` total).
- **Attempt 1 Audit Record (`runs/phase2_shiu2024_reproduction/`, rev 1, `--workers 4`, `max_wall_seconds=120.0`):** `baseline_no_stimulus` completed `30/30` (`73.04–84.06 s`, mean `77.22 s`); `sugar_grn_100hz` completed `9/13` attempted (`54.83–93.35 s`) and failed `4/13` due to `ResourceLimitError: Simulation exceeded max_wall_seconds=120.0` under 4-worker CPU/cache contention (`BENCHMARK_WALL_SECONDS=919.84 s`, exit `2`). Preserved in audit trail per `AGENTS.md` §2.
- **Attempt 2 Reproduction (`runs/phase2_shiu2024_reproduction_r2/`, rev 2, `--workers 3`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `max_wall_seconds=300.0`):**
  - `baseline_no_stimulus` (`n=30`): `52.69–56.56 s` (mean `54.49 s`)
  - `sugar_grn_100hz` (`n=30`): `55.48–66.27 s` (mean `57.74 s`)
  - `sugar_grn_100hz_silence_grn15` (`n=30`): `58.35–72.96 s` (mean `64.85 s`)
  - Overall (`n=90`): min `52.69 s`, mean `59.03 s`, max `72.96 s`; total elapsed wall time `1819.22 s` (`~30.32 min`).

## 4. Scientific Classification & Separation of Claims

Per `AGENTS.md` §2, these checks satisfy **distinct** levels and do not substitute for one another:
1. **Numerical Verification:** Confirmed Brian2 `(unless refractory)` `dg/dt` semantics and parallel vs. serial seed determinism (`tests/unit/test_shiu2024_model_fidelity.py`).
2. **Computational Reproduction:** **Achieved** for `SHIU2024-FEEDING-BENCHMARK` on `flywire_fafb_v630` against upstream commit `91bdd1e` (`overall_passed=true`, `failed_run_count=0`).
3. **Biological Validation:** **Not claimed here.** Independent experimental/behavioral perturbations, parameter sensitivity across alternative sign/conductance mappings, and non-fly translation require dedicated protocols in subsequent phases.
