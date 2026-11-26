# Evidence Register: `neuro` (`P5-NEURO-001`)

> **Research Use Only (RUO):** All L0 graph topology metrics, target/matched-control definitions, and L1 LIF ablation perturbations trace exclusively to peer-reviewed literature (`peer_review_status: peer_reviewed`) and curated local connectome tables (`flywire_fafb_v630` and specimen-isolated `malecns_v1_0`). Outputs measure structural connectome resilience and feeding-motor firing proxies (`MN9_right`, `MN9_left`), **never** Parkinson's disease, Alzheimer's disease, human aging, or clinical prognosis (`AGENTS.md` §1, §2, §10).

## Verified Peer-Reviewed Literature (`research/literature/source_register.yaml`)

| Ref ID | Citation & Identifiers | Review Status | Role in `P5-NEURO-001` |
|---|---|---|---|
| `albert2000_nature` | Albert R, Jeong H, Barabasi AL (2000), *Nature* 406(6794):378–382 · DOI: [`10.1038/35019019`](https://doi.org/10.1038/35019019) | Peer-reviewed | Establishes the structural dissociation between error tolerance under random loss and hub-targeted attack vulnerability. |
| `latora2001_prl` | Latora V, Marchiori M (2001), *Phys Rev Lett* 87(19):198701 · DOI: [`10.1103/PhysRevLett.87.198701`](https://doi.org/10.1103/PhysRevLett.87.198701) | Peer-reviewed | Defines harmonic inverse shortest-path network efficiency cleanly across disconnected or fragmented components. |
| `rubinov2010_neuroimage` | Rubinov M, Sporns O (2010), *NeuroImage* 52(3):1059–1069 · DOI: [`10.1016/j.neuroimage.2009.10.003`](https://doi.org/10.1016/j.neuroimage.2009.10.003) | Peer-reviewed | Standardizes directed weighted connectome integration, efficiency, component fragmentation, and lesion resilience measures. |
| `fornito2015_nrn` | Fornito A, Zalesky A, Breakspear M (2015), *Nat Rev Neurosci* 16(3):159–172 · DOI: [`10.1038/nrn3901`](https://doi.org/10.1038/nrn3901) | Peer-reviewed | Frames network-level hub vulnerability and selective pathway disruption strictly as structural graph hypotheses. |
| `aerts2016_brain` | Aerts H, Fias W, Caeyenberghs K, Marinazzo D (2016), *Brain* 139(12):3063–3083 · DOI: [`10.1093/brain/aww194`](https://doi.org/10.1093/brain/aww194) | Peer-reviewed | Guides comparative evaluation of focal node removal vs. edge lesions vs. matched random lesions. |
| `mckellar2020_elife` | McKellar CE et al. (2020), *eLife* 9:e54978 · DOI: [`10.7554/eLife.54978`](https://doi.org/10.7554/eLife.54978) | Peer-reviewed | Maps *Drosophila* proboscis motor neuron organization including `MN9`, anchoring the motor output readout. |
| `lin2024_nature` | Lin A, Dorkenwald S, Seung HS et al. (2024), *Nature* 634(8032):153–165 · DOI: [`10.1038/s41586-024-07968-y`](https://doi.org/10.1038/s41586-024-07968-y) | Peer-reviewed | Characterizes whole-brain *Drosophila* connectome component structure, degree distributions, and hub pathways in FlyWire FAFB. |

## Quantitative Structural Cohorts (`neuro001_flywire_v630_targets.json` & Specimen-Isolated `malecns_l0_structural_audit.json`)

- **Primary Female Brain Specimen (`flywire_fafb_v630`):** `127,400` neurons, `14,687,178` directed edges (`52,793,639` total synapses; graph SHA-256 `c8fc14b9...`).
  - **Source & Readout:** `21` right sugar GRNs (`P4-MET-001` set) -> bilateral `MN9_right` (`720575940660219265`) and `MN9_left` (`720575940645521262`), receiving `5,244` total excitatory synapses.
  - **Static L0 Premotor Hub Ranking:** Top `12` excitatory Layer-2 premotor hubs (`f2[i] * b1[i]`, selected strictly from static structure with zero activity peeking) account for `3,170 / 5,244` (`60.45%`) excitatory synapses onto bilateral `MN9` across `22` edges (top `6` hubs = `2,551 / 5,244` = `48.65%`).
  - **Matched-Random Cell Control (`12` neurons):** 1-to-1 Hungarian matching on `log1p(out_degree, out_synapses, in_degree, in_synapses)` among non-feeding `EXCITATORY_SIGN` neurons (`max|SMD| <= 0.1906`).
  - **Matched-Random Synapse Control:** Non-feeding excitatory `pre x post` Cartesian edge mask matching `24` edges / `3,157` synapses against targeted `22` edges / `3,170` synapses (`-0.41%` synapse count delta).
- **Specimen-Isolated Male CNS Structural Audit (`malecns_v1_0`):** Separate adult male connectome (`211,577` bodies, `26,028,386` edges; zero IDs pooled with FlyWire) evaluated on `R-MesoLN -> ANXXX027_L (523539) / AN08B012_R (558778)` top `12` excitatory (`ACH`) relay hubs vs. `12` Hungarian-matched controls.

## Declared Evidence & Model Gaps (`AGENTS.md` §2, §10)

1. **Structural/Acute Ablation != Progressive Neurodegeneration:** `neuron_silencing(mode="both_zero")` and `edge_mask(factor=0.0 or 0.5)` model instant static loss of synaptic transmission; slow glia-mediated clearance, axonal dieback, protein aggregation, and compensatory homeostatic scaling are unmodeled.
2. **Centrality != Functional Necessity Without Dynamics:** L0 weighted shortest-path and multi-hop flow metrics predict structural bottlenecks, which must be tested separately against L1 `shiu2024_lif` spiking dynamics.
3. **No Clinical Extrapolation:** Proboscis motor firing reduction in *Drosophila* connectomes cannot be interpreted as human motor score, Parkinsonian bradykinesia, or neurodegenerative clinical risk.
