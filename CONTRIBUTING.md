# Contributing to SYNAPSE

Thank you for your interest in contributing to **SYNAPSE**. All engineering and scientific contributions must follow the repository contract in [`AGENTS.md`](AGENTS.md).

> **Research Use Only (RUO):** Do not submit patient data, clinical advice, human efficacy claims, or unverified biological/GPU claims.

## 1. Environment Setup

Requirements: Python `3.12`, [`uv`](https://docs.astral.sh/uv/), Git, and Node `22` (for the web workbench under `apps/web`).

```sh
# Install locked Python workspace dependencies
uv sync --locked

# Optional frontend dependencies
cd apps/web && npm ci && cd ../..
```

## 2. Scientific & Architectural Rules

- **Import Direction (`AGENTS.md` §5):** Preserve the strict one-way package DAG enforced by [`test_import_boundaries.py`](tests/unit/test_import_boundaries.py):
  - `packages/synapse_core`, `packages/synapse_data` -> external libraries only (never FastAPI, SQLAlchemy, Alembic, or psycopg)
  - `packages/synapse_experiments` -> `synapse_core`, `synapse_data`
  - `packages/synapse_analysis` -> libraries (reads documented result artifacts)
  - `packages/synapse_publication` -> `synapse_analysis`
  - `packages/synapse_cli`, `apps/api`, `apps/worker` -> workspace packages
  - `apps/web` -> HTTP API only
- **Protocol Freezing & Amendments:** Keep exploratory calibration separate from confirmatory analysis. Approved protocols must be explicitly frozen (`synapse protocol freeze ... --confirm-freeze`), and frozen YAML revisions (e.g. [`P4-MET-001.frozen.yaml`](research/protocols/P4-MET-001.frozen.yaml)) are immutable.
- **No Specimen Pooling:** Never pool neuron identifiers across separate connectome reconstructions (`flywire_fafb_v630` vs. `malecns_v1_0`). Always treat `64`-bit neuron identifiers as strings in JSON and browser APIs.
- **Zero Large Data or Run Artifacts in Git:** Never commit `data/`, `runs/`, `graphify-out/`, `.env`, secrets, or binary files (`*.parquet`, `*.feather`, `*.sqlite*`).
- **Evidence Discipline:** Distinguish numerical verification, computational reproduction, and biological validation in PRs, docs, and tests.

## 3. Required Local Checks Before Opening a PR

Run all checks matching [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy packages apps/api apps/worker tests
uv run pytest -m "not slow and not gpu and not external" -v
```

For changes touching `apps/web`:

```sh
cd apps/web
npm run typecheck
npm run test
npm run build
```

When modifying architectural boundaries, schemas, or protocol conventions, document the rationale in an ADR under `docs/adr/` and update [`docs/STATUS.md`](docs/STATUS.md) (`<= 80` lines).
