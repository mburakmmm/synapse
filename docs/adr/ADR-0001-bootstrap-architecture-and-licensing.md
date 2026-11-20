# ADR-0001: Bootstrap Architecture, Licensing, and CPU Reference

- **Status:** Accepted (Phase 0 Baseline)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

SYNAPSE requires a reproducible, local-first computational neuroscience platform targeting adult *Drosophila melanogaster* connectomes and Research Use Only (RUO) mechanistic models, operable on a standard workstation (32 GiB RAM, Windows/macOS/Linux CPU baseline, optional Linux/WSL2 GPU acceleration later).

## Decision

1. **Python & Dependency Lock:** Standardize on Python `3.12` (`>=3.12,<3.13`) managed via `uv` and a single workspace `uv.lock`. Verified prebuilt Windows/macOS/Linux wheels exist for `brian2==2.10.1` (`2.11.0` requires Python `>=3.13`), `numpy`, `scipy`, `polars`, `pyarrow`, `pydantic`, `pyyaml`, `jsonschema`, and `matplotlib`.
2. **Strict Package Import DAG:**
   - `synapse_core` and `synapse_data`: external libraries only (no cross-imports between them).
   - `synapse_experiments`: depends on `synapse_core` and `synapse_data`.
   - `synapse_analysis`: external libraries only, consuming documented run artifact files.
   - `synapse_publication`: depends on `synapse_analysis` and external plotting/table libraries.
   - `synapse_cli`: coordinates workspace packages.
3. **Simulation Correctness Reference:** Use `Brian2CPUBackend` (`brian2.prefs.codegen.target = "numpy"`, `float64`) as the Phase 0 deterministic CPU reference so cross-platform execution requires no local C++ toolchain. C++ standalone / Brian2CUDA remain opt-in future backends requiring independent numerical verification.
4. **Licensing Separation:** Propose **Apache-2.0** (`LICENSE`) for SYNAPSE source code, strictly separate from upstream biological dataset licenses (`THIRD_PARTY_NOTICES.md`: FlyWire Zenodo 10676866 `cc-by-4.0`, MaleCNS `CC-BY`, Shiu et al. repo `MIT`).

## Consequences

- Phase 0 runs offline across Windows, macOS, and Linux CPU environments without compilers, Docker, PostgreSQL, or Redis.
- All biological datasets stay outside Git and require explicit user authorization before fetch.
