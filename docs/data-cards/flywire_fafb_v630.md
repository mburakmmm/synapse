# Dataset Card: `flywire_fafb_v630`

- **Dataset ID / Release:** `flywire_fafb_v630` / `v630`
- **Organism / Specimen:** Adult female *Drosophila melanogaster* (`specimen_id`: `flywire_fafb_female_01`)
- **Status:** Fetched, upstream-verified, normalized, and gate-validated (`2026-11-20`)
- **Primary Reference:** Shiu et al. (2024), *Nature*, `doi:10.1038/s41586-024-07763-9`
- **Source Commit:** `https://github.com/philshiu/Drosophila_brain_model/tree/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`
- **License / Attribution:** MIT (upstream repository code); FlyWire/FAFB data terms per upstream repository

## Verified Provenance & Checksums

| File | Role | Bytes | Upstream Checksum | Local SHA-256 |
|---|---|---|---|---|
| `2023_03_23_completeness_630_final.csv` | Raw neuron completeness | `3,057,611` | `git-blob-sha1:be745f0ce054308df21accc5c4b3883aa38498f9` | `e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb` |
| `2023_03_23_connectivity_630_final.parquet` | Raw connectivity | `86,630,944` | `git-blob-sha1:8b4d9531bc0acbda7c2074ae577e6ac9e2fca166` | `94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3` |

- **Local Canonical Manifest SHA-256:** `f6965c945c801571371f6f593cdc9d1fc2f6cb8cbe32def898d1640069b4acf9`
- **Canonical Sparse Graph SHA-256 (`DirectedConnectomeGraph`):** `c8fc14b90aff0200250987dceea9e929129d17c3d09f75354f15251393a00552`

## Reconciled Counts & Quality Gate Summary

- **Neurons (`neurons.parquet`):** `127,400` (`completed_neuron_count = 127,400`, `incomplete_neuron_count = 0`, 64-bit string IDs verified unique & index-consistent)
- **Directed Edges (`connections.parquet`):** `14,687,178` (`duplicate_pairs_collapsed = 0`, `self_loop_count = 0`, `reciprocal_directed_edge_count = 3,899,348` across `1,949,674` reciprocal pairs)
- **Total Synapses:** `52,793,639`
- **Quarantined Records (`quarantine.parquet`):** `0`
- **Sign-Only Neurotransmitter Breakdown:**
  - `EXCITATORY_SIGN`: `86,543`
  - `INHIBITORY_SIGN`: `40,472`
  - `UNKNOWN` (`no_outgoing_edges_for_sign`): `385`
  - `CONFLICTING_SIGN`: `0`
- **Reference Anchors Verified:** `21 / 21` Shiu sugar-sensing GRNs present; `MN9` (`720575940660219265`) present

## Known Limitations

- Upstream `v630` provides binary `Excitatory` sign (`+1` / `-1`), not chemical transmitter identities or postsynaptic receptor affinities.
- Structural synapse count is not a measured conductance; `region` and per-edge `confidence` are omitted upstream.
- Excluded `sez_neurons.pickle` (`5,114` B) per `AGENTS.md` §13 (no untrusted pickle deserialization).
- Must never be pooled with `v783` or `malecns_v1_0` node IDs.
