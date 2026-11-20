# ADR-0003: Phase 1 Connectome Canonical Schemas, Sign Encoding, and Subgraphs

- **Status:** Accepted (Phase 1 Baseline)
- **Date:** 2026-11-20
- **Owners:** SYNAPSE Maintainers

## Context

Phase 1 introduces multi-million-edge biological connectome datasets (`flywire_fafb_v630` with `14,687,178` edges; `malecns_v1_0` with ~1.11 GB flat connectome tables). Python-loop row iteration and unauthenticated raw files fail performance and provenance standards.

## Decision

1. **Vectorized Canonical Pipeline & Graph Construction:**
   - Normalize and gate-check canonical Parquet tables via vectorized Polars joins (`validate_canonical_dataset`, `FlyWireV630Adapter`, `MaleCNSV1Adapter`).
   - Construct sparse CSR matrices (`W[post_idx, pre_idx]`) directly from NumPy index/count arrays (`DirectedConnectomeGraph.from_arrays`) and hash graphs via canonical permutation-invariant CSR byte hashing (`graph_sha256()`).
2. **Sign-Only vs. Named Neurotransmitter Preservation:**
   - Preserve upstream FlyWire v630 binary `Excitatory` flags as explicit sign-only categories (`EXCITATORY_SIGN`, `INHIBITORY_SIGN`, `CONFLICTING_SIGN`, `UNKNOWN`) rather than fabricating chemical identities (`ACH`/`GABA`/`GLUT`).
   - Map MaleCNS v1.0 `consensus_nt` / `predicted_nt` strings to `ACH`, `GABA`, `GLUT`, `DA`, `OCT`, `SER`, or `UNKNOWN`, preserving `raw_neurotransmitter_label` and explicit `missingness` reasons.
   - `UNKNOWN`, `CONFLICTING_SIGN`, and `None` remain unmapped in `DEFAULT_SIGN_MAP` so `unknown_nt_policy` handles them explicitly without silent excitatory fallback.
3. **Upstream Checksum Verification & Non-Deserialization:**
   - Authenticate raw transfers against upstream `git-blob-sha1:` (GitHub API blob SHA) or `md5:` (GCS/Zenodo) BEFORE atomic commit (`download_file_atomic`), recording parent raw hashes in `parent_raw_files` without duplicating gigabyte raw inputs inside `curated/`.
   - Exclude `sez_neurons.pickle` per `AGENTS.md` §13 (no untrusted pickle deserialization).
4. **Bounded Subgraphs with Explicit Omission Accounting:**
   - `extract_bounded_subgraph()` records `selection_rule`, `hop_limit`, `min_synapse_threshold`, `direction`, `boundary_policy="induced"`, `source_graph_sha256`, `subgraph_sha256`, exact `omitted_incoming_*` and `omitted_outgoing_*` counts, and explicit `isolation_limitations`.

## Consequences

- `flywire_fafb_v630` loads, verifies, hashes, and slices bounded subgraphs cleanly within standard workstation memory.
- Specimen namespaces (`flywire_fafb_female_01` vs `malecns_male_01`) remain strictly isolated.
