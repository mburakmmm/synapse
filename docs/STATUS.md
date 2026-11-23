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
| **Phase 5B (`P5-SLEEP-001`)** | L3 circadian-homeostatic oscillator + shift-work & L1 `malecns_v1_0` pilot | **L3 Verified + L1 Pilot Complete (Draft Freeze Pending)** | 4/4 L3 gates + 5 shift arms; `24/24` L1 pilot runs + 3 bundles ([Sleep Pilot](../research/modules/sleep/pilot_report.md)) |
| **Phase 5B (`P5-ADD-001`)** | L2 MB dopamine plasticity + conditioning/extinction/reinstatement & L1 `malecns_v1_0` pilot | **L2 Verified + L1 Pilot Complete (Draft Freeze Pending)** | 5/5 L2 gates + 5 arms; `24/24` L1 pilot runs + 3 bundles ([Addiction Pilot](../research/modules/addiction/pilot_report.md)) |
| **Phase 5C (`Neuro/Pharma/Stress`)** | Targeted ablation, receptor kinetics & stress circuitry | **Planned** | Gated on module evidence registers and target validation (`AGENTS.md` §10) |

## Phase 5B Sleep Summary (`P5-SLEEP-001-PILOT`, RUO)

- **L3 Oscillator & L1 Pilot:** All 4 L3 gates passed (`tau_DD = 24.1346 h`, `tau_LD = 24.0171 h`, `CT 15 = -2.3591 h`, `CT 21 = +2.3431 h`, rebound `+0.1625`); `24/24` `malecns_v1_0` runs (`sham = 0`) showed `DN1p -> TuTuB_b` suppression (`-12.917 / -11.250 Hz`), `EdgeMask` rescue, and `50 Hz` `TuBu01/ExR1/ER5` drive ([ADR-0007](adr/ADR-0007-phase5b-sleep-circadian-homeostatic-coupling.md)). Draft [`P5-SLEEP-001.yaml`](../research/protocols/P5-SLEEP-001.yaml) awaits human freeze.

## Phase 5B Addiction Summary (`P5-ADD-001-PILOT`, RUO)

- **L2 Plasticity (`mb_dopamine_plasticity_v1`):** All 5 gates passed (`max|dW|=1.947e-4`, `PI_acq=+0.33123`, `PI_ext=+0.045171` preserving `w_avoid=0.334152`, `PI_reinst=+0.26580 > +0.16480` spontaneous, `sham=0.0`, `yoked=+6.2e-5`, `dan_blocked=0.0`) ([ADR-0008](adr/ADR-0008-phase5b-addiction-mb-plasticity-coupling.md)).
- **L1 Pilot (`24/24` runs on `malecns_v1_0`, `N=3`, `sham_max_spikes=0`):** Early `[0.1,0.2)s` `MBON02_L` silenced under acquisition (`26.67->0.00 Hz`) vs. matched KC controls (`|SMD|<=0.13225`, `26.67 Hz`) and invariant `CS-` (`63.33 Hz`); full-trial `[0.0,0.6]s` reflected recurrent `MBON14_R` acq (`+71.111 Hz`), ext drop (`-193.333 Hz`), reinst rebound (`+178.889 Hz`), and null yoked/matched (`-0.556 Hz`). Draft [`P5-ADD-001.yaml`](../research/protocols/P5-ADD-001.yaml) (`120` runs, est. `1.60 h` at `workers=3`) awaits human freeze.
