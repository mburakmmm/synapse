# ADR-0002: Graphify Navigation & Bounded Context Discipline

- **Status:** Accepted (Phase 0 Baseline)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

AI coding agents and maintainers need fast structural dependency discovery across packages, schemas, protocols, and tests without reading whole files or pulling binary scientific data into navigation indexes.

## Decision

1. **External Tool Pinning:** Keep Graphify (`graphifyy 0.9.113`, verified via `graphify --version`) installed via `uv tool install` outside `pyproject.toml`, `uv.lock`, and runtime containers. Do not auto-upgrade during research runs.
2. **Code-Only Local Indexing:** Default to `GRAPHIFY_BACKEND=none` (`graphify extract . --code-only` and `graphify update .`) and disable query logging (`GRAPHIFY_QUERY_LOG_DISABLE=1`) so no private files, raw datasets, or query logs leave the machine.
3. **Strict Exclusions & Bounded Queries:**
   - Track `.graphifyignore` excluding `graphify-out/`, `.git/`, `.venv/`, `data/`, `runs/`, `artifacts/`, `research/manuscripts/`, private literature/protocols, and binary extensions (`*.parquet`, `*.npy`, `*.h5`, `*.pdf`, `*.png`, `*.svg`).
   - Track `.graphifyrc` with `query_budget=1200` and `query_depth=2` (verified supported in `graphify/rcfile.py` of `graphifyy 0.9.113`).
   - Keep `graphify-out/` gitignored.
4. **Scientific Non-Authority:** Graphify is strictly a code navigation aid—never the biological connectome engine and never scientific evidence. Agents verify exact source files and tests before making claims.

## Consequences

- Repository navigation remains bounded and reproducible while biological datasets and run artifacts never enter the code graph.
