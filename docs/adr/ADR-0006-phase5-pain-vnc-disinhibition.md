# ADR-0006: Phase 5A Pain Module — Adult VNC GABA Disinhibition on `malecns_v1_0`

- **Status:** Accepted (Phase 5A Exploratory Baseline; Confirmatory Freeze Pending Human Approval)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

Phase 5 (`AGENTS.md` §10, §15) advances into **Pain** circuitry after Phases 0–4, asking whether suppressing inhibitory GABAergic inputs onto ascending pain/escape pathways lowers activation threshold or amplifies stimulus-evoked motor/ascending firing, while explicitly separating **acute pathway disinhibition** from **cell-death proxies**. Female `flywire_fafb_v630` lacks the ventral nerve cord (VNC) and contains only binary sign labels (`±1`), whereas `malecns_v1_0` provides the full central brain + VNC with explicit `GABA` predictions and `MesoLN` middle-leg afferents.

## Decision

1. **Dedicated Single-Specimen Target (`malecns_v1_0`, Never Pooled):**
   - Ground `P5-PAIN-001` strictly in `malecns_v1_0` (`211,577` bodies, `26,028,386` edges) using right middle-leg tactile afferents (`MesoLN`, `rootSide == "R"`) driving `26` feedforward VNC-intrinsic `GABA` interneurons onto ascending relays (`ANXXX027`, `AN08B012`) and jump motor neuron `TTMn`.
   - Explicitly document in [`evidence_register.md`](../../research/modules/pain/evidence_register.md) that `MesoLN` afferents lack verified `ppk`/`TrpA1` nociceptor subtype tags and that `Jones et al. (2025)` (`doi:10.1101/2025.10.28.684868`) is a non-peer-reviewed bioRxiv preprint.
2. **Distinguish Disinhibition (`EdgeMaskModulation`) from Cell Death (`NeuronSilencing`):**
   - Implement [`EdgeMaskModulation`](../../packages/synapse_core/models.py) (`kind: "edge_mask"`) in `synapse_core` and `synapse_experiments` so protocols can zero *only* specific directed `pre -> post` edges (`26` VNC `GABA` -> `6` ascending relays) without silencing those interneurons' intra-VNC connections.
   - Retain `NeuronSilencing(mode="both_zero")` separately as an ablation/cell-death proxy (`Khuong et al., 2019`).
3. **Windowed Pre/Stimulus/Post Persistence Analysis (`synapse_analysis.windows`):**
   - Add [`compute_windowed_response_metrics`](../../packages/synapse_analysis/windows.py) to measure baseline `[0.0, 0.1)`, stimulus `[0.1, 0.6)`, and post-stimulus `[0.6, 0.8]` rates plus persistence duration cleanly from `spikes.parquet`, preserving `failed_run_count`.
4. **Matched VNC `GABA` Control Policy:**
   - Select `26` `vnc_intrinsic` `GABA` controls via `select_matched_control_neurons` excluding `pre_of_ascending6` (`0` direct edges onto `AN08B012`/`ANXXX027`) with `exclude_1hop_downstream_of_targets=False` (`candidate_pool_per_target=200`) so all 4 `|SMD| <= 0.0970`.

## Consequences

- Exploratory pilot (`24/24` runs, `N = 3`) revealed clean separation between pathway-specific `acute_edge_mask` (elevating `523539` `51.3 Hz`, `558778` `28.0 Hz`, `10592` `17.3 Hz`) and global `gaba_cell_death` (elevating `523539` `43.3 Hz` while lowering `10592` `9.3 Hz`), empirically validating why both interventions belong in `P5-PAIN-001.yaml`.
- Unfrozen confirmatory [`P5-PAIN-001.yaml`](../../research/protocols/P5-PAIN-001.yaml) remains `status: draft` until explicit human confirmation (`--confirm-freeze`).
