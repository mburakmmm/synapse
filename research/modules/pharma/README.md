# Phase 5C-2 Pharma Module (`P5-PHARMA-001`, Research Use Only)

- **Scope:** Dose-independent mechanistic receptor kinetics (`receptor_conductance_modulation_v1`, `L2`) coupled to an isolated adult male *Drosophila* connectome circuit (`malecns_v1_0`, `synapse_lif_v1`, `L1`), testing bidirectional `Rdl` (`GABA_A`) modulation, orthogonal `nAChR` (`ACH`) attenuation, dual-target Bliss independence, and anatomically matched off-pathway GABA specificity controls.
- **Safety Guard (`AGENTS.md` §10):** `named_compound_gate_enabled = False` — strictly dimensionless normalized ratios (`[A]/EC50`, `[B]/Ki`, `[I]/IC50`, `[M]/Km`). No named human drugs, clinical dosages, or clinical efficacy claims.
- **Target Set:** [`target_sets/pharma001_malecns_v1_targets.json`](target_sets/pharma001_malecns_v1_targets.json) (`30` MesoLN `ACH` sensory neurons, `26` feedforward `GABA` interneurons, `26` `matched_vnc_gaba_controls`, primary ascending readouts `523539`, `558778`, `10592`).
- **Documentation & Governance:**
  - [ADR-0010](../../../docs/adr/ADR-0010-phase5c-pharma-receptor-conductance-modulation.md)
  - [Evidence Register](evidence_register.md)
  - [L2 Model Card](model_card.md)
  - [L2 + L1 Pilot Report](pilot_report.md)
- **Protocols:**
  - Executed Pilot: [`research/protocols/P5-PHARMA-001-pilot.yaml`](../../protocols/P5-PHARMA-001-pilot.yaml) (`N=3`, `24/24` succeeded)
  - Confirmatory Draft (unfrozen): [`research/protocols/P5-PHARMA-001.yaml`](../../protocols/P5-PHARMA-001.yaml) (`status: draft`, `N=15`, `120` runs, awaits human freeze)
