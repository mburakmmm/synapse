# SYNAPSE Status

> Authoritative phase tracker ([`AGENTS.md`](../AGENTS.md)). Keep `<= 80` lines.

| Phase | Scope | Gate Status | Primary Evidence |
|---|---|---|---|
| **Phase 0** | Bootstrap, package DAG, `synthetic_microcircuit_v1`, CI, Graphify nav | **Verified** | Unit/integration checks on offline synthetic fixture |
| **Phase 1** | Local `flywire_fafb_v630` & `malecns_v1_0` ingestion & Parquet/CSR normalization | **Verified** | Data gates passed (`0` quarantined rows); local `data/` gitignored ([Data Cards](data-cards/flywire_fafb_v630.md)) |
| **Phase 2** | Whole-brain `flywire_fafb_v630` computational reproduction of Shiu et al. (2024) | **Computationally Reproduced** | `90/90` runs passed (`failed_run_count = 0`) ([Report](validation/shiu2024_reproduction_report.md)) |
| **Phase 3** | Protocol freeze, CLI run planner, PostgreSQL `SKIP LOCKED`, FastAPI, Worker, React/Plotly UI | **Verified** | API/worker/UI suites + Docker backup/restore parity ([ADR-0005](adr/ADR-0005-phase3-research-laboratory-architecture.md)) |
| **Phase 4 (`P4-MET-001`)** | Metabolic feeding circuit matched controls, confirmatory (`N=30`), robustness (`N=6`), MaleCNS audit | **Confirmatory Simulation Complete** | `180/180` confirmatory + `36/36` robustness runs; *not* biological validation ([Metabolic Report](../research/modules/metabolic/confirmatory_report.md)) |
| **Phase 5A (`P5-PAIN-001`)** | Pain VNC GABAergic disinhibition (`EdgeMaskModulation`) vs. cell death on `malecns_v1_0` | **Confirmatory Simulation Complete** | `120/120` confirmatory (`6/6` primary `q = 9.9990e-05`) + `36/36` robustness runs ([Pain Report](../research/modules/pain/confirmatory_report.md)) |
| **Phase 5B+** | Sleep & Addiction modules | **Planned** | Gated on primary literature review & module-specific negative controls |

## Phase 5A Summary (`P5-PAIN-001`, RUO Computational Simulation)

- **Confirmatory Run:** Frozen [`P5-PAIN-001.frozen.yaml`](../research/protocols/P5-PAIN-001.frozen.yaml) (`protocol_sha256: a379c7e1c7b264859fe777730464cd8d34807dc1772818b5c4bb4b978ed683cf`, `master = 20261131`, `N = 15`, `git_commit: 5a878cd`, `git_dirty = false`) completed `120/120` runs (`0` failed, `8271.70 s`, `sham_max_spikes = 0`) into gitignored `runs/phase5_pain001_confirmatory/`.
- **Primary Contrasts (BH-FDR `q = 9.9990e-05`):** Pathway-selective `acute_edge_mask` elevated ascending output `523539` (`+20.667 Hz` vs. baseline & matched ctrl; stim `19.067 -> 51.467 Hz`) and `558778` (`+3.833 Hz` vs. baseline, `+3.333 Hz` vs. ctrl), while matched-control GABA ablation remained null (`p = 1.0000` / `0.3544`).
- **Disinhibition vs. Cell-Death Dissociation:** Global `gaba_cell_death` selectively suppressed `10592` (`-4.500 Hz`, `p = 2.9997e-04`) whereas selective `acute_edge_mask` raised it (`+1.417 Hz`, `p = 0.0213`); post-stimulus `[0.6, 0.8] s` firing remained `<= 1.667 Hz` across L1 LIF models.
- **Exploratory Robustness (`36/36` runs, `N = 6`, `2269.22 s`):** Positive `acute_edge_mask` deltas on `523539` (`+15.208` to `+20.833 Hz`, `p = 0.03125`) and `558778` (`+2.708` to `+3.750 Hz`, `p = 0.03125`) held across `shiu2024_lif` and `±10% w_syn_v` (`0.2475`/`0.3025 mV`).

## Known Limitations & Immediate Next Tasks

1. **RUO Limits:** Single male specimen (`malecns_v1_0`), L1 LIF without receptor subtypes or chronic injury remodeling, and `Jones et al. 2025` non-peer-reviewed preprint status documented in [`evidence_register.md`](../research/modules/pain/evidence_register.md).
2. **Next:** Verify Ubuntu CI + begin Phase 5B literature & anatomical scoping (Sleep / Addiction modules) only after explicit approval.
