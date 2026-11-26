# Phase 5C Neuro Pilot Report (`P5-NEURO-001-PILOT`, L0 Topology + L1 FlyWire Motor Degradation)

> **Claim Classification (RUO):** L0 metrics were verified analytically (`5/5` gates) and evaluated non-destructively on local `flywire_fafb_v630` and specimen-isolated `malecns_v1_0` Parquet/CSR graphs. L1 outputs summarize **`24/24` exploratory CPU simulations** (`N = 3` paired seeds × `8` conditions, `failed_run_count = 0`, `sham_max_spikes = 0`) under [`P5-NEURO-001-pilot.yaml`](../../protocols/P5-NEURO-001-pilot.yaml). Not biological or clinical neurodegeneration validation (`AGENTS.md` §2, §10).

## 1. L0 Topology & Exact Ablation Audit (`neuro_topology_ablation_v1`)

- **Parameter Manifest SHA-256:** `f29e9b9e4abf7919015258180118498608de785e03e59dbe6e5451797c051e8c` (`overall_passed = true` across all `5` analytic gates).
- **FlyWire `flywire_fafb_v630` Progressive Attack (`runs/phase5c_neuro001_l0_topology/l0_ablation_summary.json`):**

| Condition / Step | Removed Nodes | Removed Edges | Removed Synapses | Weighted Eff Ratio | 3-Hop Exc Flow Ratio | `MN9` Exc Syn Retention | Reachability |
|---|---:|---:|---:|---:|---:|---:|---:|
| `intact_baseline` | `0` | `0` | `0.0` | `1.0000` | `1.0000` | `1.0000` | `1.000` |
| `targeted_cell_loss (k=6)` | `6` | `2,861` | `35,294.0` | `0.7698` | `0.1721` | `0.5135` | `1.000` |
| `targeted_cell_loss (k=12)` | `12` | `5,237` | `59,593.0` | `0.6027` | `0.0843` | `0.3955` | `1.000` |
| `matched_random_cell_loss (k=12)` | `12` | `5,515` | `58,592.0` | `1.0000` | `1.0000` | `1.0000` | `1.000` |
| `targeted_synapse_loss_50pct` | `0` | `22` | `1,585.0` | `0.9583` | `0.5419` | `0.6977` | `1.000` |
| `targeted_synapse_loss_100pct` | `0` | `22` | `3,170.0` | `0.6740` | `0.0847` | `0.3955` | `1.000` |
| `matched_random_synapse_loss` | `0` | `24` | `3,157.0` | `1.0000` | `1.0000` | `1.0000` | `1.000` |

- **Specimen-Isolated `malecns_v1_0` L0 Audit (`malecns_l0_structural_audit.json`):** On male VNC `R-MesoLN -> ANXXX027_L (523539) / AN08B012_R (558778)`, `k = 12` `ACH` hub loss (`max|SMD| = 0.1094`) yielded `weighted_eff_ratio = 0.9198` and `three_hop_flow_ratio = 0.4218` (`matched_random_cell_loss k=12`: `1.0000 / 1.0000`; `targeted_synapse_loss_100pct`: `0.9632 / 0.6169`), reflecting higher parallel multi-path bypass density than FlyWire `MN9` premotor bottlenecks.

## 2. L1 `flywire_fafb_v630` Pilot Execution & Paired Motor Contrasts (`N = 3`, `1.0 s`)

- **Run Integrity & Cost:** `24/24` `COMPLETE` (`failed_run_count = 0`, `sham_max_spikes = 0`), `wall_total_s = 1478.413 s`, `run_wall_mean_s = 61.601 s` (`min = 55.965 s`, `max = 70.418 s`; ~`8.6 min` wall on `3` CPU workers). Confirmatory `N = 15` (`120` runs) projects to `~0.68 h` on `3` workers.
- **Per-Condition L1 Motor Rates vs. L0 Retention:**

| Condition | `MN9_right` Mean ± SD (Hz) | `MN9_right` Retention | `MN9_left` Mean ± SD (Hz) | `MN9_left` Retention | L0 Weighted Eff Ratio |
|---|---:|---:|---:|---:|---:|
| `sham_zero_stimulus` | `0.000 ± 0.000` | `0.000` | `0.000 ± 0.000` | `0.000` | — |
| `intact_baseline_100hz` | `69.000 ± 1.000` | `1.000` | `53.333 ± 1.155` | `1.000` | `1.0000` |
| `matched_random_cell_loss_12` | `70.333 ± 2.517` | `1.019` | `50.000 ± 3.606` | `0.938` | `1.0000` |
| `matched_random_synapse_loss` | `69.000 ± 1.000` | `1.000` | `53.333 ± 1.155` | `1.000` | `1.0000` |
| `targeted_synapse_loss_50pct` | `46.000 ± 5.292` | `0.667` | `24.667 ± 4.163` | `0.463` | `0.9583` |
| `targeted_synapse_loss_100pct` | `0.000 ± 0.000` | `0.000` | `0.000 ± 0.000` | `0.000` | `0.6740` |
| `targeted_cell_loss_top6` | `0.000 ± 0.000` | `0.000` | `0.667 ± 1.155` | `0.013` | `0.7698` |
| `targeted_cell_loss_top12` | `0.000 ± 0.000` | `0.000` | `0.000 ± 0.000` | `0.000` | `0.6027` |

- **Key Paired Contrasts (`synapse analysis run` + 3 Export Bundles):**
  - `mn9r_cell_loss_top12_vs_intact`: **`-69.000 Hz`** (`[-70.000, -68.000]`); `mn9l`: **`-53.333 Hz`** (`[-54.000, -52.000]`).
  - `mn9r_cell_loss_vs_matched_ctrl` (specificity): **`-70.333 Hz`** (`[-74.000, -67.000]`); `mn9l`: **`-50.000 Hz`** (`[-52.000, -47.000]`).
  - `mn9r_syn_loss_50pct_vs_intact` (graded synapse loss): **`-23.000 Hz`** (`[-27.000, -18.000]`); `mn9l`: **`-28.667 Hz`** (`[-33.000, -25.000]`).
  - `mn9r_syn_loss_100pct_vs_intact`: **`-69.000 Hz`** (`[-70.000, -68.000]`); `mn9r_cell_vs_synapse_dissociation`: **`+0.000 Hz`** (threshold silence reached via either `22` focal edges / `3,170` syn or `12` full somata / `59,593` syn, whereas upstream L0 global route efficiency diverges `0.6740` vs. `0.6027`).
  - Negative controls: `mn9r_matched_ctrl_cell_vs_intact` = `+1.333 Hz` (`[-1.000, +4.000]`); `mn9r_matched_ctrl_syn_vs_intact` = `+0.000 Hz` (`[+0.000, +0.000]`).
- **Evidence Bundles Exported (`runs/phase5c_neuro001_exploratory_pilot/`):** `bundle_mn9r_cell_loss_top12_vs_intact`, `bundle_mn9r_cell_loss_vs_matched_ctrl`, `bundle_mn9r_cell_vs_synapse_dissociation`.

## 3. Confirmatory Next Step

[`P5-NEURO-001.yaml`](../../protocols/P5-NEURO-001.yaml) (`status: draft`, `N = 15`, `master = 20261161`, `120` runs, est. `0.68 h` at `workers = 3`) remains **unfrozen** and queued alongside `P5-SLEEP-001.yaml` and `P5-ADD-001.yaml` pending explicit human approval.
