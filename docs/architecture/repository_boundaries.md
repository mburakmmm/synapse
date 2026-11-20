# Repository Architecture Boundaries

This document tracks the implemented Phase 0 package boundaries and planned extensions (`AGENTS.md` §5).

## Implemented Phase 0 Package Import DAG

```text
synapse_cli
 ├── synapse_core        (libraries only: numpy, scipy, brian2, pydantic)
 ├── synapse_data        (libraries only: polars, pyarrow, jsonschema)
 ├── synapse_experiments (synapse_core, synapse_data, polars, pyyaml, jsonschema)
 ├── synapse_analysis    (libraries only: numpy, polars; reads run artifacts)
 └── synapse_publication (synapse_analysis, matplotlib, polars)
```

Enforced automatically by `tests/unit/test_import_boundaries.py`.

## Sparse Matrix Orientation Invariant

`DirectedConnectomeGraph.adjacency_counts` uses **postsynaptic rows, presynaptic columns** (`W[post_idx, pre_idx]`), so matrix multiplication `W @ pre_activity` yields postsynaptic input.

## Planned (Not Yet Implemented)

- `apps/api/` (FastAPI + PostgreSQL/Alembic metadata store — Phase 3)
- `apps/worker/` (bounded subprocess worker — Phase 3)
- `apps/web/` (React + TypeScript + Plotly.js exploratory UI — Phase 3)
- `research/modules/{pain,sleep,addiction,neuro,pharma,stress}/` (Phases 4–5)
