# Phase 1/2 Benchmark Proposal: Shiu et al. (2024) Feeding Circuit Reproduction

> **Status:** Draft proposal awaiting maintainer approval before dataset download (`AGENTS.md` §17.5). Expected numerical outcomes are intentionally NOT invented prior to fetching/inspecting published figures and running the reproduction.

## 1. Reference Provenance Inspected (`2026-11-20`)

- **Paper:** Shiu et al. (2024), *Nature*, `doi:10.1038/s41586-024-07763-9`
- **Repository:** `https://github.com/philshiu/Drosophila_brain_model`
- **Inspected Commit:** `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960` (`2024-09-14T13:47:44Z`, License: `MIT`)
- **Primary Dataset for Reproduction:** FlyWire **v630** (`2023_03_23_completeness_630_final.csv` + `2023_03_23_connectivity_630_final.parquet`), NOT `v783`, per `AGENTS.md` §3 ("must not silently replace the historical reproduction data").

## 2. Observed Upstream Model Implementation Details (`model.py`)

Direct inspection of upstream `model.py` (`91bdd1e7...`) identified exact equations and implementation subtleties that Phase 2 reproduction must account for explicitly:

1. **Equations & Parameters (`default_params`):**
   - `t_run = 1000 * ms`, `n_run = 30`, `v_0 = -52 * mV`, `v_rst = -52 * mV`, `v_th = -45 * mV`, `t_mbr = 20 * ms`, `tau = 5 * ms`, `t_rfc = 2.2 * ms`, `t_dly = 1.8 * ms`, `w_syn = 0.275 * mV`, `r_poi = 150 * Hz`, `r_poi2 = 0 * Hz`, `f_poi = 250`.
   - Upstream equations:
     - `dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)`
     - `dg/dt = -g / tau : volt (unless refractory)`
     - `eq_th = 'v > v_th'`, `eq_rst = 'v = v_rst; w = 0; g = 0 * mV'`, `method='linear'`.
   - **Notable upstream details for Phase 2 ADR:**
     - Upstream `dg/dt` carries `(unless refractory)`, whereas canonical exponential decay normally omits `(unless refractory)`.
     - Upstream `eq_rst` contains `w = 0` on `NeuronGroup` (note: `w` is a synaptic variable on `Synapses`, not defined in `NeuronGroup` `eqs`).
     - Upstream `silence(slnc, syn)` sets `syn.w[' {i} == i'] = 0*mV` (zeroes **outgoing** synapses from `i`), whereas `Readme.md` states "sets all synaptic connections to and from those neurons to zero".
     - `sez_neurons.pickle` (`5,114` bytes) uses Python `pickle`: per `AGENTS.md` §13 ("no untrusted deserialization"), Phase 1 will audit and convert this file into plain JSON/CSV inside an isolated check rather than loading raw pickle in worker runs.

## 3. Storage & Compute Budget (Local Workstation)

- **Target Hardware:** 32 GiB system RAM, NVIDIA RTX 4060 Laptop GPU (8 GiB VRAM, driver 591.59). CPU reference is primary (`brian2_cpu`); GPU acceleration is out of scope until Phase 3+.
- **Download Footprint (`flywire_fafb_v630`):**
  - `2023_03_23_completeness_630_final.csv`: `3,057,611` bytes (~2.9 MiB)
  - `2023_03_23_connectivity_630_final.parquet`: `86,630,944` bytes (~82.6 MiB)
  - `sez_neurons.pickle` (optional reference list): `5,114` bytes
  - **Total v630 download:** ~`89.7` MB (`89,693,669` bytes).
- **Optional Later Datasets (NOT needed for initial v630 benchmark):**
  - `flywire_fafb_v783` core files (Zenodo `10676866`): ~`853.1` MB (`proofread_root_ids_783.npy` + `proofread_connections_783.feather`).
  - `flywire_synapses_783.feather`: `9.49` GB (excluded by default; unnecessary for edge-aggregated LIF).

## 4. Approval Gate Checklist Before Phase 1 Fetch

1. Maintainer approves downloading `flywire_fafb_v630` (~89.7 MB) into gitignored `data/raw/flywire_fafb_v630/`.
2. Inspect `example.ipynb` and `figures.ipynb` from commit `91bdd1e7...` to lock exact sugar/water GRN & MN9 FlyWire IDs, stimulus rates, and published numeric acceptance tolerances in `research/protocols/P1-BENCH-SHIU2024-draft.yaml`.
