# Software Manuscript Outline: SYNAPSE Computational Research Workbench (RUO)

> **DRAFT SOFTWARE PAPER OUTLINE (`AGENTS.md` §12):** Summarizes only implemented, verified software architecture, tests, and reproducibility controls on disk. Authorship, CRediT, funding, ethics, and submission require explicit human approval.

## 1. Software Scope & Scientific Motivation

- **Mission:** Local-first, open-source (**Apache-2.0** proposed) computational laboratory for reproducible *Drosophila melanogaster* connectome simulations (**Research Use Only**; zero clinical/patient ingestion).
- **Strict Specimen Isolation:** Separate SHA-256 provenance and non-pooled node namespaces for female `flywire_fafb_v630` and male `malecns_v1_0`.

## 2. Layered Software Architecture

- **Pure Core DAG (`packages/`):** `synapse_core` (L0 topology/ablation, L1 Brian2 LIF, L2 MB plasticity & dose-independent receptor kinetics, L3 circadian-homeostatic & reactive-scope stress ODEs), `synapse_data`, `synapse_experiments`, `synapse_analysis`, `synapse_publication`, `synapse_cli` — zero FastAPI/SQLAlchemy imports in scientific packages (AST-enforced).
- **Orchestration & UI (`apps/`):** Versioned FastAPI `/api/v1` service, durable SQLite/PostgreSQL worker queue (`FOR UPDATE SKIP LOCKED`), Alembic migrations, Docker Compose deployment, and bilingual EN/TR React + Plotly + lazy-loaded Three.js workbench (Simple + Expert modes).

## 3. Verification, Reproducibility & Open-Science Archival

- **Published Benchmark Reproduction:** `SHIU2024-FEEDING-BENCHMARK` (`90/90` runs on `flywire_fafb_v630`, `overall_passed=true`).
- **Confirmatory & Exploratory Pipelines:** Pre-registered frozen confirmatory runs (`P4-MET-001` `180/180`, `P5-PAIN-001` `120/120`) plus `N=3` pilot baselines across Sleep, Addiction, Neuro, Pharma, and Stress.
- **Publication & Security Gates:** Evidence bundle SHA-256/path-containment verification, `source_register.yaml` citation audit, zip-slip-safe release archival (`synapse export release-archive`), and loopback-only SQLite/PostgreSQL backup/restore verification (`scripts/backup_restore_verify.py`).

## 4. Governance Placeholders (`[HUMAN AUTHOR INPUT REQUIRED]`)

- **Authors / ORCID / CRediT / License Sign-Off / Zenodo DOI / AI Assistance Disclosure:** `[TO BE COMPLETED BY HUMAN MAINTAINERS BEFORE EXTERNAL SUBMISSION]`
