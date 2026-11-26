# Third-Party Notices and Data Licensing

SYNAPSE software is proposed under the **Apache-2.0** license (`LICENSE`), subject to maintainer approval. External biological datasets, reference models, and third-party libraries retain their respective upstream licenses and are **not** relicensed by SYNAPSE or bundled into this repository.

Retrieved and verified metadata as of **2026-11-20**:

## Software & Simulation Dependencies

| Component | Upstream Source | License | Role in SYNAPSE |
|---|---|---|---|
| Brian2 (`2.10.1` pinned lock range `>=2.10,<2.11`) | https://brian2.readthedocs.io/ | CeCILL-2.1 | Reference CPU LIF simulation engine |
| `philshiu/Drosophila_brain_model` (commit `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`) | https://github.com/philshiu/Drosophila_brain_model | MIT | Reference LIF equations and `flywire_fafb_v630` reproduction baseline (`sez_neurons.pickle` excluded) |
| Graphify (`graphifyy 0.9.113`) | https://github.com/Graphify-Labs/graphify | Upstream OSS (external dev tool) | Local code-only navigation index; strictly outside runtime dependency lock |
| Python scientific, API & DB packages (`NumPy`, `SciPy`, `Polars`, `PyArrow`, `Pydantic`, `PyYAML`, `jsonschema`, `FastAPI`, `SQLAlchemy`, `Alembic`, `psycopg`, `Matplotlib`) | `pyproject.toml` / `uv.lock` | Respective OSS licenses | Pinned in `uv.lock` for offline-reproducible CPU execution and metadata orchestration |
| Frontend & container dependencies (`React`, `Vite`, `Plotly.js`, `Three.js`, `Vitest`, `Playwright`, `PostgreSQL`) | `apps/web/package-lock.json` / `compose.yaml` | Respective OSS licenses | Local exploratory workbench, 3D topology projection, and containerized metadata persistence |

## Biological Connectome Data Sources (Not Redistributed in Git)

| Dataset | Source | License | Verification & Repository Scope |
|---|---|---|---|
| FlyWire / FAFB connectivity & completeness snapshots (`v630`: `2023_03_23_completeness_630_final.csv`, `2023_03_23_connectivity_630_final.parquet`) | https://github.com/philshiu/Drosophila_brain_model (`91bdd1e`) & https://zenodo.org/records/10676866 (`v783`) | `MIT` (repo code); `CC-BY-4.0` (FlyWire v783 release) / upstream FlyWire terms | Adult female *Drosophila* brain; upstream git-blob SHA-1 and local SHA-256 verified during Phase 1 (`data/` gitignored; requires explicit local fetch approval) |
| Janelia MaleCNS v1.0 (`body-annotations`, `body-neurotransmitters`, `connectome-weights`, `minconf-0.5`, released `2026-06-08`) | https://male-cns.janelia.org/download/ · `doi:10.1016/j.cell.2026.08.015` | `CC-BY-4.0` (FlyEM / HHMI Janelia, University of Cambridge, MRC LMB, Google Research) | Adult male *Drosophila* central nervous system (`scope="annotated_bodies"`); GCS MD5 and local SHA-256 verified during Phase 1 (`data/` gitignored; never pooled with FlyWire IDs) |

Any reuse of upstream code or derived connectome artifacts must preserve upstream copyright notices, license texts, and dataset attributions.
