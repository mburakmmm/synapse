# Neurodegeneration & Resilience Module (`neuro`)

- **UI / Gate Status:** `experimental` (Phase 5C **L0 topology, fragmentation & exact ablation audit gates verified `5/5`**, specimen-isolated `malecns_v1_0` L0 structural audit completed, and **L1 `flywire_fafb_v630` exploratory pilot `24/24` completed**; confirmatory freeze of [`P5-NEURO-001.yaml`](../../protocols/P5-NEURO-001.yaml) pending explicit human approval; L0 efficiency and `MN9_right` / `MN9_left` LIF firing are computational *Drosophila* circuit proxies, **not** clinical Parkinson's, Alzheimer's, aging, or human prognosis; `RUO`).
- **Primary Female Specimen:** `flywire_fafb_v630` (`127,400` neurons, `14,687,178` edges, `52,793,639` synapses) anchored on the reproduced Shiu et al. (2024) sugar GRN -> `MN9` feeding-motor circuit.
- **Specimen-Isolated Male L0 Cross-Check:** `malecns_v1_0` (`211,577` bodies, `26,028,386` edges; zero IDs pooled with FlyWire) on `R-MesoLN -> ANXXX027_L / AN08B012_R`.

## Key Findings (`P5-NEURO-001`)

- **Stage 1 — Verified L0 Topology, Fragmentation & Exact Ablation Audit (`neuro_topology_ablation_v1`):**
  - All 5 analytic gates passed (`chain_cut_disconnects`, `parallel_bridge_node_vs_edge_dissociation`, `asymmetric_orientation_and_reverse_dijkstra_parity`, `fractional_synapse_scaling_monotonicity`, and `isolated_control_invariance_and_immutability`).
  - Progressive attack on static Layer-2 `flywire_fafb_v630` premotor hubs (`k = 0 -> 12`, removing `5,237` edges / `59,593` syn) dropped weighted pathway efficiency to `0.6027` (`-39.7%`) and 3-hop excitatory flow to `0.0843` (`-91.6%`), while `12` Hungarian-matched control cells (`max|SMD| = 0.1906`, removing `5,515` edges / `58,592` syn) preserved `1.0000 / 1.0000`.
  - Severing only the `22` direct `hub -> MN9` edges (`3,170` syn; `18.8x` fewer synapses than whole-cell ablation) reproduced the `3-hop` bottleneck (`0.0847`) while retaining higher alternate-path weighted efficiency (`0.6740` vs. `0.6027`). On `malecns_v1_0`, `k = 12` VNC `ACH` hub ablation preserved higher parallel redundancy (`eff_ratio = 0.9198`, `3hop_flow_ratio = 0.4218`).
- **Stage 2 — Grounded L1 Functional Motor-Degradation Pilot (`P5-NEURO-001-PILOT`, `N = 3`, `24/24` runs):**
  - Intact `100 Hz` sugar-GRN drive reproduced Phase 2 `MN9_right = 69.000 Hz` / `MN9_left = 53.333 Hz`; `sham_zero_stimulus` emitted `0` spikes across `3/3` seeds.
  - Whole-cell hub loss collapsed bilateral `MN9` (`top12`: `0.000 / 0.000 Hz`; `top6`: `0.000 / 0.667 Hz`), `50%` direct `hub -> MN9` synapse loss produced graded suppression (`46.000 / 24.667 Hz`), `100%` direct `hub -> MN9` synapse loss also silenced `MN9` (`0.000 / 0.000 Hz`), whereas matched-random cell (`70.333 / 50.000 Hz`) and matched-random synapse (`69.000 / 53.333 Hz`) controls preserved motor output.

## Artifacts

- Exploratory & L0 Verification Report: [`pilot_report.md`](pilot_report.md)
- Target & Matched Control Set: [`neuro001_flywire_v630_targets.json`](target_sets/neuro001_flywire_v630_targets.json)
- Literature, Model & ADR Docs: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md), [`ADR-0009`](../../../docs/adr/ADR-0009-phase5c-neuro-ablation-and-topology.md)
- Protocols: [`P5-NEURO-001-pilot.yaml`](../../protocols/P5-NEURO-001-pilot.yaml) (`draft` exploratory), [`P5-NEURO-001.yaml`](../../protocols/P5-NEURO-001.yaml) (`draft` confirmatory — unfrozen pending approval)
