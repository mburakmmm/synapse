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
| **Phase 5B+ (`Addiction`)** | Reward-learning / conditioning & reinstatement module | **Planned** | Gated on explicit plasticity rule, yoked sham controls & literature review |

## Phase 5B Sleep Summary (`P5-SLEEP-001-PILOT`, RUO)

- **L3 Oscillator Gates (`leloup_goldbeter_1998_two_process_v1`):** All 4 pre-shift-work gates passed (`tau_DD = 24.1346 h`, convergence `0.0 h`, `tau_LD = 24.0171 h`, `CT 15 = -2.3591 h`, `CT 21 = +2.3431 h`, 12 h deprivation rest rebound `+0.1625`); rotating 3-day `+8 h` shift reached `10.814 h` max error without stable re-entrainment ([ADR-0007](adr/ADR-0007-phase5b-sleep-circadian-homeostatic-coupling.md)).
- **L1 Exploratory Pilot (`24/24` runs on `malecns_v1_0`, `N = 3`, `sham_max_spikes = 0`):** `DN1p` inhibited `TuTuB_b` (`22794`: `102.083 -> 89.167 Hz`, `520699`: `100.417 -> 89.167 Hz`), matched `GLUT` controls (`|SMD| <= 0.0304`) were null (`101.667 / 101.250 Hz`), and `DN1pB->TuBu01/TuTuB_b` masking rescued firing (`101.667 / 101.250 Hz`); `50 Hz` misaligned light + debt recruited `TuBu01` (`+14.583 Hz`), `ExR1` (`+2.917 Hz`), and `ER5` (`+2.083 Hz`).
- **Draft Confirmatory Protocol:** [`P5-SLEEP-001.yaml`](../research/protocols/P5-SLEEP-001.yaml) remains `status: draft` (`120` runs, est. `~2.18 h` at `workers = 3`); freeze & run require explicit human sign-off.
