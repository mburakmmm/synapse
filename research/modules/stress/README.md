# Phase 5C-3 Stress Module (`P5-STRESS-001`, Research Use Only)

- **Scope:** Reactive-scope allostatic load ODEs (`stress_allostatic_reactive_scope_v1`, `L3`) coupled to an isolated adult male *Drosophila* connectome defensive escape/freezing circuit (`malecns_v1_0`, `synapse_lif_v1`, `L1`).
- **Safety Guard (`AGENTS.md` §1, §10):** `diagnostic_label_guard_enabled = True` — all metrics strictly measure fly-level defensive arousal, escape (`DNp01`, `DNp11`), and freezing (`DNp09`) circuit proxies, with human clinical anxiety/depression diagnoses excluded. Peptidergic neurons (`DH44`, `IPC`, `DSK`) carry `UNKNOWN` NT tags in MaleCNS and remain unmodeled.
- **Target Set:** [`target_sets/stress001_malecns_v1_targets.json`](target_sets/stress001_malecns_v1_targets.json) (`20` `LC4` + `20` `LC9` threat sensory `ACH`, `30` defensive `GABA`/`GLUT` gate inputs, `40` matched visual `ACH` controls `max|SMD|=0.0676`, `30` matched off-pathway `GABA`/`GLUT` controls `max|SMD|=0.1279`).
- **Documentation & Governance:**
  - [ADR-0011](../../../docs/adr/ADR-0011-phase5c-stress-allostatic-defensive-circuitry.md)
  - [Evidence Register](evidence_register.md)
  - [L3 Model Card](model_card.md)
  - [L3 + L1 Pilot Report](pilot_report.md)
- **Protocols:**
  - Executed Pilot: [`research/protocols/P5-STRESS-001-pilot.yaml`](../../protocols/P5-STRESS-001-pilot.yaml) (`N=3`, `24/24` succeeded)
  - Confirmatory Draft (unfrozen): [`research/protocols/P5-STRESS-001.yaml`](../../protocols/P5-STRESS-001.yaml) (`status: draft`, `N=15`, `120` runs, awaits human freeze)
