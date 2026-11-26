# SYNAPSE Status

> Authoritative phase tracker ([`AGENTS.md`](../AGENTS.md)). Keep `<= 80` lines.

| Phase | Scope | Gate Status | Primary Evidence |
|---|---|---|---|
| **Phase 0–3** | Bootstrap, FlyWire v630 & MaleCNS v1.0 ingestion, Shiu 2024 `90/90` LIF, FastAPI/Worker/UI | **Verified / Reproduced** | `90/90` bench PASS ([Shiu Report](validation/shiu2024_reproduction_report.md)); Docker backup/restore ([ADR-0005](adr/ADR-0005-phase3-research-laboratory-architecture.md)) |
| **Phase 4 (`P4-MET-001`)** | Metabolic feeding gain + matched controls (`N=30` conf., `N=6` robust.) | **Confirmatory Simulation Complete** | `180/180` + `36/36` runs; *not* biological validation ([Metabolic Report](../research/modules/metabolic/confirmatory_report.md)) |
| **Phase 5A (`P5-PAIN-001`)** | Pain VNC GABA disinhibition vs. cell death on `malecns_v1_0` (`N=15` conf., `N=6` robust.) | **Confirmatory Simulation Complete** | `120/120` (`6/6` `q=9.9990e-05`) + `36/36` runs ([Pain Report](../research/modules/pain/confirmatory_report.md)) |
| **Phase 5B (`P5-SLEEP-001`)** | L3 circadian-homeostatic oscillator (`4/4`) + L1 `malecns_v1_0` `24/24` pilot | **L3 Verified + L1 Pilot Complete (Draft Queued)** | `tau_DD=24.1346 h`, `tau_LD=24.0171 h`, `24/24` `sham=0` ([Sleep Pilot](../research/modules/sleep/pilot_report.md)) |
| **Phase 5B (`P5-ADD-001`)** | L2 MB dopamine plasticity (`5/5`) + L1 `malecns_v1_0` `24/24` pilot | **L2 Verified + L1 Pilot Complete (Draft Queued)** | `PI_acq=+0.33123`, `PI_ext=+0.045171`, `PI_reinst=+0.2658` ([Addiction Pilot](../research/modules/addiction/pilot_report.md)) |
| **Phase 5C-1 (`P5-NEURO-001`)** | L0 fragmentation/ablation (`5/5`) + `malecns_v1_0` L0 audit + L1 `flywire_fafb_v630` `24/24` pilot | **L0 Verified + L1 Pilot Complete (Draft Queued)** | Hub `k=12` `eff=0.6027`, `MN9_R -69.0 Hz`, `ctrl +1.3 Hz` ([Neuro Pilot](../research/modules/neuro/pilot_report.md)) |
| **Phase 5C-2/3 (`Pharma/Stress`)** | Receptor kinetics & stress circuitry | **Planned** | Gated on module evidence registers and target validation (`AGENTS.md` §10) |

## Phase 5C-1 Neuro Summary (`P5-NEURO-001-PILOT`, RUO)

- **L0 Topology & MaleCNS Audit (`neuro_topology_ablation_v1`):** `5/5` analytic gates passed ([ADR-0009](adr/ADR-0009-phase5c-neuro-ablation-and-topology.md)); FlyWire `k=12` premotor hubs (`5,237` edges / `59,593` syn) dropped `eff=0.6027` & `3hop=0.0843`, focal `22`-edge/`3,170`-syn mask hit `3hop=0.0847` (`eff=0.6740`), matched controls stayed `1.0000`; specimen-isolated `malecns_v1_0` (`max|SMD|=0.1094`) kept `eff=0.9198`.
- **L1 Pilot (`24/24` runs on `flywire_fafb_v630`, `N=3`, `sham=0`):** Intact `MN9_R/L = 69.000/53.333 Hz`; `top12` & `100% syn` both silenced `MN9` (`0.000/0.000 Hz`, specificity `-70.333/-50.000 Hz`), `50% syn` gave graded drop (`46.000/24.667 Hz`), while matched cell (`70.333/50.000 Hz`) & synapse (`69.000/53.333 Hz`) controls remained intact.

## Deferred Confirmatory Queue (User Reminder — Unfrozen Drafts)

1. [`P5-SLEEP-001.yaml`](../research/protocols/P5-SLEEP-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~2.17 h`), awaits human freeze & execution.
2. [`P5-ADD-001.yaml`](../research/protocols/P5-ADD-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.60 h`), awaits human freeze & execution.
3. [`P5-NEURO-001.yaml`](../research/protocols/P5-NEURO-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~0.68 h`), awaits human freeze & execution.
