# ADR-0004: Phase 2 Shiu et al. (2024) Reproduction Fidelity and Execution Controls

- **Status:** Accepted (Phase 2 Reproduction Gate)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

Phase 2 requires reproducing the published adult *Drosophila* sugar-GRN feeding circuit simulation from Shiu et al. (*Nature*, 2024; DOI `10.1038/s41586-024-07763-9`) on `flywire_fafb_v630` using deterministic CPU execution (`brian2 2.10.1`). Inspection of the upstream reference commit `philshiu/Drosophila_brain_model@91bdd1e7dcf193f3e7ca5a8933497fcef63b7960` revealed three critical implementation and operational details:

1. Upstream `model.py` defines `dg/dt = -g / tau_syn : volt (unless refractory)` and solves with `method='linear'` (`dt = 0.1 ms`), whereas Phase 0's canonical `synapse_lif_v1` omits `(unless refractory)` on `dg/dt` and uses `solver='exact'`.
2. Upstream `sez_neurons.pickle` violates `AGENTS.md` §13 (prohibiting untrusted pickle deserialization).
3. No local C/C++ compiler toolchain (`cl`/`gcc`/`g++`/`clang`) is available on the baseline Windows host, requiring Brian2's pure-NumPy target (`prefs.codegen.target = "numpy"`). Under `--workers 4` on this 8-core (4 P-core + 4 E-core) CPU, Attempt 1 hit `max_wall_seconds=120.0` on 4 of 13 attempted active runs (`BENCHMARK_WALL_SECONDS=919.84s`, exit `2`).

## Decision

1. **Preserve Both Model Formulations via Explicit Parameter Flag (`dg_unless_refractory`):**
   - Add `dg_unless_refractory: bool = False` to `LIFParameters` and provide `LIFParameters.shiu2024_reference()` (`model_id="shiu2024_lif"`, `solver="linear"`, `dg_unless_refractory=True`, `parameter_manifest_sha256=12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`).
   - Keep `synapse_lif_v1` (`dg_unless_refractory=False`, `solver="exact"`) unchanged so Phase 0 benchmarks remain bitwise preserved.
   - Document verified Brian2 `2.10.1` codegen semantics in `synapse_core/brian2_backend.py`: placing `(unless refractory)` on `dg/dt` (`_LIF_EQUATIONS_SHIU`) causes Brian2 `synapses_pre` to gate postsynaptic `on_pre="g += w"` increments by `not_refractory`, discarding synaptic inputs arriving while the postsynaptic neuron is refractory (`_postsynaptic_idx[not_refractory]`).
2. **Exclude `sez_neurons.pickle` & Record Clean Notebook Provenance:**
   - Extract the 21 sugar GRN IDs and MN9 left/right IDs directly from plain-JSON upstream notebooks (`example.ipynb` and `figures.ipynb` at `91bdd1e`) without downloading or unpickling `sez_neurons.pickle`.
3. **Pure-NumPy CPU Reference & Protocol Revision 2 Operational Resource Cap:**
   - Standardize Phase 2 CPU reproduction on `Brian2CPUBackend` (`prefs.codegen.target = "numpy"`).
   - Retain failed Attempt 1 artifacts (`runs/phase2_shiu2024_reproduction/`) untouched in the local audit trail per `AGENTS.md` §2.
   - Issue `P2-BENCH-SHIU2024` revision `2` (`research/protocols/P2-BENCH-SHIU2024.yaml`) increasing only `resources.max_wall_seconds` from `120.0` to `300.0` (leaving all biological/model parameters, `parameter_manifest_sha256`, seeds, conditions, and predeclared tolerances unchanged), and execute Attempt 2 (`runs/phase2_shiu2024_reproduction_r2/`) with `--workers 3` and single-threaded BLAS/OpenMP (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`).

## Consequences

- `synapse benchmark reproduce` on `P2-BENCH-SHIU2024` rev `2` completed `90/90` runs (`0` failures, `52.69s`–`72.96s` per run) and passed every predeclared comparison and directional contrast gate (`overall_passed=True`).
- Computational reproduction on `flywire_fafb_v630` is established without altering tolerances or conflating computational reproduction with wet-lab biological validation.
