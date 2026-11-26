# Model Card: `neuro` Module (`neuro_topology_ablation_v1` L0 + `shiu2024_lif` L1 on `flywire_fafb_v630`)

> **Research Use Only (RUO):** Couples a verified L0 graph fragmentation and exact node/edge ablation audit model (`neuro_topology_ablation_v1`) with validated L1 LIF feeding-motor simulations (`shiu2024_lif`) on `flywire_fafb_v630`, alongside a specimen-isolated L0 structural cross-check on `malecns_v1_0`. **Not** a human neurodegeneration, Parkinson's, Alzheimer's, or clinical diagnostic model (`AGENTS.md` §1, §7.1, §10).

## 1. L0 Topology, Fragmentation & Exact Ablation Audit (`neuro_topology_ablation_v1`)

- **Model Identity:** `model_id = "neuro_topology_ablation_v1"`, `revision = "1.0"`, `model_level = "L0"`, canonical parameter manifest SHA-256 `f29e9b9e4abf7919015258180118498608de785e03e59dbe6e5451797c051e8c`.
- **Implementation:** `packages/synapse_core/topology.py` (`TopologyAnalysisParameters`, `evaluate_graph_ablation`, `run_progressive_ablation_curve`, `verify_topology_ablation_gates`).
- **Metrics & Audit Invariants:**
  - **Surviving-Node Component Fragmentation:** Computes `wcc_count`, `largest_wcc_fraction` (`largest_wcc_nodes / n_total_nodes`), `scc_count`, and `largest_scc_fraction` strictly over surviving active nodes (`active_mask`) so ablated nodes do not inflate living component counts.
  - **Directional Excitatory Pathway Efficiency:** Evaluates inverse-synapse-weight edge distance (`1 / effective_synapse_count`) using orientation-invariant Dijkstra (`row=post, col=pre` reverse traversal when `|target| < |source|`, exact forward traversal otherwise), reporting `reachability_fraction`, `unweighted_harmonic_efficiency`, `weighted_pathway_efficiency`, `two_hop_exc_flow`, `three_hop_exc_flow`, and `target_exc_in_synapses`.
  - **Immutable Edge Audit:** Every ablation step records `removed_neuron_ids`, `removed_node_count`, `removed_edge_count`, fractional/integer `removed_synapse_count`, and `removed_edges_sha256` across all removed/attenuated edges without mutating `DirectedConnectomeGraph`.
- **Verified Pre-Experiment Gates (5/5 PASS):**
  - `chain_cut_disconnects`: 5-node chain cut yields `reachability = 0.0`, `wcc_count = 2`, `largest_wcc_fraction = 0.4`, `removed_edge_count = 2`.
  - `parallel_bridge_node_vs_edge_dissociation`: diamond bridge edge cut (`1` edge) retains `3-hop_flow = 8000.0`, `weighted_eff = 6.666667` vs. full node ablation (`3` edges, `3-hop_flow = 0.0`, `weighted_eff = 4.0`).
  - `asymmetric_orientation_and_reverse_dijkstra_parity`: forward/reverse Dijkstra agree to `< 1e-12` (`7.261904762`), while transpose direction (`T -> S`) drops `reachability` to `0.0`.
  - `fractional_synapse_scaling_monotonicity`: `factor` `1.0 -> 0.5 -> 0.0` scales `two_hop_exc_flow` linearly (`200.0 -> 100.0 -> 0.0`).
  - `isolated_control_invariance_and_immutability`: off-pathway control ablation preserves exact `graph_sha256()` and identical pathway metrics (`6.666666667`).

## 2. L1 Connectome-Grounded Motor Readout (`shiu2024_lif` on `flywire_fafb_v630`)

- **Model Identity:** `shiu2024_lif` (`revision = "1.0"`, SHA-256 `12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`), `brian2_cpu` (`solver = "linear"`, `dt = 0.0001 s`, `dg_unless_refractory = true`, `w_syn_v = 0.275 mV`).
- **Interventions Compared (`1.0 s` trials, `100 Hz` sugar-GRN drive):**
  - `neuron_silencing(mode="both_zero")` cleanly separates whole-cell ablation (zeroing all incident incoming & outgoing synapses across `top-6` or `top-12` hubs vs. `12` Hungarian-matched controls `max|SMD| = 0.1906`) from
  - `edge_mask(pre=top12, post=[MN9_R, MN9_L], factor=0.5 | 0.0)` modeling fractional/complete premotor synapse loss against a degree/synapse-matched non-feeding edge mask (`24` edges / `3,157` syn vs. `22` edges / `3,170` syn).
- **Assumptions & Limits:** Acute static structural loss in a single female brain specimen; lacks slow glia clearance, tau/alpha-synuclein aggregation kinetics, axonal transport deficits, and homeostatic plasticity.
