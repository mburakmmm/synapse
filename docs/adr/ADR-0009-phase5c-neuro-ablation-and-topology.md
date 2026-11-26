# ADR-0009: Phase 5C Neuro Module — L0 Ablation & Fragmentation Engine with L1 `flywire_fafb_v630` Motor Readout

- **Status:** Accepted (Phase 5C-1 L0 Topology Gates Verified + `malecns_v1_0` L0 Audit + L1 `flywire_fafb_v630` Exploratory Pilot Architecture; Confirmatory Freeze Pending Human Approval)
- **Date:** 2026-11-23
- **Owners:** SYNAPSE Maintainers

## Context

`AGENTS.md` §1, §2, §10, and §15 require that the **Neuro** module (`neuro`):
1. Record **exact** nodes and edges removed under targeted vs. matched-random ablation, track connectome fragmentation (`WCC`, `SCC`) and pathway efficiency (`L0`), and pair structural predictions against a **previously validated functional motor readout** (`L1`) rather than conflating graph centrality with functional necessity (`AGENTS.md` §9).
2. Explicitly separate **whole-cell ablation** (removing all incoming and outgoing edges of a neuron, `mode="both_zero"`) from **targeted synapse loss** onto the readout (`edge_mask`), paired against structurally matched non-target cell and synapse controls.
3. Keep all interpretations strictly **Research Use Only (RUO)** at the *Drosophila* circuit level (`MN9_right` / `MN9_left` proboscis extension motor proxy; zero Parkinson's, Alzheimer's, aging, or clinical human diagnosis claims), and preserve strict specimen isolation between `flywire_fafb_v630` and `malecns_v1_0`.

## Decision

1. **Non-Mutating L0 Topology & Ablation Audit Kernel (`packages/synapse_core/topology.py`):**
   - Implement `TopologyAnalysisParameters` (`neuro_topology_ablation_v1`, `model_level = "L0"`, `sha256: f29e9b9e4abf7919015258180118498608de785e03e59dbe6e5451797c051e8c`), `evaluate_graph_ablation`, `run_progressive_ablation_curve`, and fail-closed `verify_topology_ablation_gates` (5 analytic gates: chain-cut disconnection, diamond node-vs-edge dissociation, forward/reverse Dijkstra parity & transpose detection, fractional synapse monotonicity, and off-pathway control invariance).
   - Compute whole-graph `connected_components` strictly on surviving active vertices (`active_mask`) so ablated nodes do not appear as artificial living 1-node components, and use `(row=post, col=pre)` reverse traversal whenever `|target| < |source|` (`~10.5x` speedup on `21 -> 2` whole-brain shortest paths while mathematically identical to forward traversal).
   - Hash ALL removed/attenuated `(pre_id, post_id, lost_synapses)` entries into `removed_edges_sha256` on every attack step.

2. **Grounded Functional Readout on `flywire_fafb_v630` + Specimen-Isolated `malecns_v1_0` L0 Cross-Check:**
   - Anchor the L1 functional arm on the computationally reproduced Shiu et al. (2024) feeding circuit (`flywire_fafb_v630`, `shiu2024_lif`, `100 Hz` sugar-GRN drive -> `MN9_right` / `MN9_left`, where Phase 2 already established exact target rates `68.833 / 49.533 Hz`).
   - Identify static Layer-2 excitatory premotor hubs (`f2[i] * b1[i]` with zero neural activity peeking; top `12` hubs supply `3,170 / 5,244 = 60.45%` of excitatory synapses onto bilateral `MN9` across `22` edges).
   - Compare progressive targeted cell death (`top6`, `top12`), `12` Hungarian-matched control neurons (`max|SMD| = 0.1906`), `50%` and `100%` targeted `hub -> MN9` synapse loss (`edge_mask`), and a non-feeding `24`-edge / `3,157`-synapse matched control edge mask (`-0.41%` synapse count delta).
   - Run an independent, specimen-isolated L0 structural attack audit on `malecns_v1_0` (`R-MesoLN -> ANXXX027_L / AN08B012_R`, `max|SMD| = 0.1094`) to characterize regional connectome redundancy differences without cross-specimen ID pooling.

## Consequences

- Provides complete causal linkage from exact removed structural sets (`removed_edges_sha256`, weighted efficiency, 3-hop flow, target synapse retention) to paired L1 motor-output degradation (`synapse_analysis` + export bundles).
- Establishes an explicit mechanistic dissociation between focal synapse loss (`22` edges, `3,170` syn) and whole-cell soma ablation (`5,237` edges, `59,593` syn).
- Does not model progressive intracellular neurodegeneration kinetics; confirmatory protocol `P5-NEURO-001.yaml` remains `status: draft` until human freeze approval.
