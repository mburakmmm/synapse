# Changelog

All notable milestone changes to **SYNAPSE** (**Research Use Only**) are documented here.
Versioning tracks software (`0.1.0.dev0`), schemas (`1.0`), datasets, protocols, and models separately.

## `[0.1.0.dev0]` — 2026-11-26

### Phases 0–3: Foundation, Connectome Adapters & Research Workbench
- Implemented strict layered package DAG (`synapse_core`, `synapse_data`, `synapse_experiments`, `synapse_analysis`, `synapse_publication`, `synapse_cli`) with AST boundary tests.
- Verified FlyWire/FAFB `v630` and Janelia MaleCNS `v1.0` SHA-256 dataset ingestion, canonical Parquet tables, and bounded subgraph extraction.
- Reproduced `SHIU2024-FEEDING-BENCHMARK` (`90/90` runs on `flywire_fafb_v630`, `overall_passed=true`) via Brian2 CPU (`shiu2024_lif`).
- Delivered FastAPI `/api/v1` service, PostgreSQL/SQLite job queue + worker isolation, Alembic migrations, Docker Compose backup/restore verification (`scripts/backup_restore_verify.py`), and bilingual EN/TR React + Three.js + Plotly workbench (Simple + Expert modes).

### Phases 4–5C: Translational Neuroscience & Mechanistic Modules (RUO)
- **Phase 4 (`P4-MET-001`):** Pre-registered confirmatory `N=30` (`180/180` runs) + `N=6` robustness (`36/36` runs) on `flywire_fafb_v630`.
- **Phase 5A (`P5-PAIN-001`):** Pre-registered confirmatory `N=15` (`120/120` runs, `6/6` primary contrasts BH-FDR `q=9.9990e-05`) + `N=6` robustness (`36/36` runs) on `malecns_v1_0`.
- **Phase 5B (`P5-SLEEP-001`, `P5-ADD-001`):** L3 circadian-homeostatic ODEs (`4/4` gates) and L2 mushroom-body three-factor plasticity (`5/5` gates), each paired with `24/24` MaleCNS exploratory pilots and unfrozen confirmatory drafts.
- **Phase 5C (`P5-NEURO-001`, `P5-PHARMA-001`, `P5-STRESS-001`):** L0 network fragmentation/ablation (`5/5` gates), L2 dose-independent receptor-conductance kinetics (`5/5` gates, `named_compound_gate_enabled=False`), and L3 reactive-scope allostatic load ODEs (`5/5` gates, `diagnostic_label_guard_enabled=True`), each paired with `24/24` exploratory pilots and unfrozen confirmatory drafts.

### Phase 6: Open-Science Publication, Archival & Governance
- Added bundle SHA-256/containment verification (`verify_evidence_bundle`), citation register auditing (`audit_citation_register`), evidence-linked methods synthesis, and deterministic ZIP release archival (`build_publication_release_archive`, `verify_publication_release_archive`).
- Added CLI `synapse export {verify-bundle, verify-citations, release-archive, verify-archive}`, API `GET /api/v1/publication/readiness`, Web Publication Readiness panel (EN/TR), `pain001_outline.md`, `synapse_platform_software_outline.md`, and `ADR-0012`.
