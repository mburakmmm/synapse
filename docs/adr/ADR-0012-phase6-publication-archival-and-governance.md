# ADR-0012: Phase 6 Open-Science Publication Archival, Verification & Governance Gates

> Status: Accepted (Local Release-Ready; External Publication Human-Gated)  
> Date: 2026-11-26  
> Scope: `synapse_publication`, `synapse_cli`, `synapse_api`, `apps/web`, `research/manuscripts/`

## Context

`AGENTS.md` §§12–16 require reproducible open-science exports containing evidence-linked methods, checksummed source tables and SVG/PNG figures, citation audits distinguishing preprints, software/environment locks, and strict exclusion of restricted raw connectome data (`data/`) and secrets (`.env`, keys), while gating Zenodo DOI minting, journal submission, and authorship sign-off on explicit human approval.

## Decision

1. **Publication Verification & Archival Engine (`packages/synapse_publication/archive.py`):**
   - `verify_evidence_bundle` validates `provenance/bundle_manifest.json`, path containment, byte sizes, SHA-256 hashes, and required figure/table/reproducibility artifacts.
   - `audit_citation_register` audits `research/literature/source_register.yaml` for unique IDs, locators (`doi`/`url`/`pmid`), `claim_scope`, and explicit preprint flagging (`preprint_not_peer_reviewed`).
   - `build_publication_release_archive` & `verify_publication_release_archive` package allowlisted open-science governance, protocols, module reports, target sets, manuscript outlines, and verified evidence bundles into a deterministic, zip-slip-safe `.zip` + `ARCHIVE_MANIFEST.json`, while hard-blocking `data/`, `.env*`, key files, and `spikes.parquet`.
   - `generate_evidence_linked_methods` synthesizes factual Markdown tables directly from `analysis_manifest.json` with explicit `[HUMAN AUTHOR INPUT REQUIRED]` governance placeholders.

2. **CLI, API & Web Readiness Surface:**
   - Expose `synapse export {verify-bundle, verify-citations, release-archive, verify-archive}` in `synapse_cli`.
   - Expose `GET /api/v1/publication/readiness` in `synapse_api` and a bilingual EN/TR **Phase 6 Open-Science & Publication Readiness** panel inside `ResultsExportsView` surfacing bundle/citation checks, tracked manuscript outlines, governance artifacts, and explicit human approval gates.

## Consequences

- Zero raw connectome weights or secrets can enter archival bundles; every quantitative claim in manuscript outlines traces deterministically to disk artifacts.
- External DOI archiving, journal submission, and freezing the 5 remaining Phase 5B–5C confirmatory drafts remain explicitly gated on human sign-off.
