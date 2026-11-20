# Dataset Card: `malecns_v1_0`

- **Dataset ID / Release:** `malecns_v1_0` / `v1.0` (released `2026-06-08`)
- **Organism / Specimen:** Adult male *Drosophila melanogaster* central nervous system (`specimen_id`: `malecns_male_01`)
- **Status:** Fetched, MD5-verified, normalized (`scope="annotated_bodies"`), and gate-validated (`2026-11-20`)
- **Primary Sources:** https://male-cns.janelia.org/download/ · Release notes: https://male-cns.janelia.org/release/ · Paper: `doi:10.1016/j.cell.2026.08.015`
- **License / Attribution:** `CC-BY-4.0` (FlyEM / HHMI Janelia, University of Cambridge, MRC LMB, Google Research)

## Verified Provenance & Checksums

| File | Role | Bytes | Upstream Checksum (GCS MD5) | Local SHA-256 |
|---|---|---|---|---|
| `body-annotations-male-cns-v1.0-minconf-0.5.feather` | Curated neuron annotations | `14,483,314` | `md5:50a7718770c57220f160ba4f431ab89e` | `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` |
| `body-neurotransmitters-male-cns-v1.0.feather` | Per-body NT predictions | `43,282,834` | `md5:3d842b12fe5c49eefade528d7dd24a1f` | `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621` |
| `connectome-weights-male-cns-v1.0-minconf-0.5.feather` | Directed body weights | `1,051,241,946` | `md5:f30e9dcca25cfd021bf1e7b3d975599e` | `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` |

- **Local Canonical Manifest SHA-256:** `6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`
- **Canonical Sparse Graph SHA-256 (`DirectedConnectomeGraph`):** `ef5324051bbaaf960cc12754f1017b14700dc725c2c85e5afce75fb5a45256ce`

## Reconciled Counts & Scope Accounting (`scope="annotated_bodies"`)

- **Raw File Totals:** `211,577` curated annotation rows; `1,835,518` raw NT rows; `151,856,684` raw weight rows (`311,833,243` total raw synapses across `88,384,522` segmented bodies).
- **Normalized Canonical Connectome (`annotated_bodies`):**
  - **Neurons (`neurons.parquet`):** `211,577` (`Traced`: `165,122`, `Orphan`: `15,925`, `Glia`: `11,864`, `Unimportant`: `10,751`, `malecns_v1_annotated` [null status]: `5,472`, `Assign`: `1,832`, `Anchor`: `611`)
  - **Directed Edges (`connections.parquet`):** `26,028,386` (`duplicate_pairs_collapsed = 0`, `self_loop_count = 112`)
  - **Total Canonical Synapses:** `125,365,933`
  - **Excluded Unannotated-Fragment Traffic:** `125,828,298` edges (`186,467,310` synapses) involving segments outside `body-annotations`
  - **Quarantined Records (`quarantine.parquet`):** `0`
- **Neurotransmitter Breakdown (`neurotransmitters.parquet`):**
  - `ACH`: `104,173` · `GLUT`: `29,443` · `GABA`: `22,186` · `HIST`: `8,024` · `DA`: `396` · `OCT`: `101` · `SER`: `48` · `UNKNOWN`: `47,206`
- **Excluded Optional Site-Level Files:** `syn-points` (~12.7 GB), `syn-partners` (~6.8 GB), `tbar-neurotransmitters` (~2.7 GB), `body-stats` (~778 MB).

## Known Limitations & Non-Pooling Rules

- Separate male specimen: node IDs (`bodyId`) must never be pooled or directly equated with female FlyWire/FAFB IDs.
- Default `annotated_bodies` scope excludes unannotated EM twig/orphan segments explicitly recorded above.
- `minconf-0.5` weights omit neuropil breakdown and per-edge confidence values; `HIST` is stored canonically without assuming a global excitatory/inhibitory sign.
- One male and one female specimen cannot establish population-level sex differences.
