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
| **Phase 5C-2 (`P5-PHARMA-001`)** | L2 dose-independent kinetics (`5/5`) + L1 `malecns_v1_0` `24/24` pilot | **L2 Verified + L1 Pilot Complete (Draft Queued)** | Schild `1.000000`, `Rdl` `+21.1`/`-5.0 Hz`, Bliss `0.7692` vs `0.6982` ([Pharma Pilot](../research/modules/pharma/pilot_report.md)) |
| **Phase 5C-3 (`P5-STRESS-001`)** | L3 reactive-scope allostasis (`5/5`) + L1 `malecns_v1_0` `24/24` defensive pilot | **L3 Verified + L1 Pilot Complete (Draft Queued)** | `80.21x` L3 load, `DNp01` `12.2->63.1 Hz`, `off-inh` `12.5 Hz` ([Stress Pilot](../research/modules/stress/pilot_report.md)) |

## Phase 5C-3 Stress Summary (`P5-STRESS-001-PILOT`, RUO)

- **L3 Reactive-Scope ODE (`stress_allostatic_reactive_scope_v1`):** `5/5` gates passed with `diagnostic_label_guard_enabled=True` ([ADR-0011](adr/ADR-0011-phase5c-stress-allostatic-defensive-circuitry.md)); `RK45` diff `1.184e-05`, chronic load `80.21x` acute, reserve washout `0.545 -> 0.934`.
- **L1 Pilot (`24/24` runs on `malecns_v1_0`, `N=3`, `sham=0`):** `DNp01` rose from `12.222 Hz` (`30 Hz`) to `46.667/57.500 Hz` (`0.5x`/`0.0x` inh. reserve) and `63.056 Hz` (sensitized); off-pathway inh. control remained null (`12.500 Hz`), while non-defensive visual `60 Hz` left `DNp09` freezing at `0.000 Hz` (with `>=2`-hop `DNp01` spillover noted).

## Deferred Confirmatory Queue (User Reminder — Unfrozen Drafts)

1. [`P5-SLEEP-001.yaml`](../research/protocols/P5-SLEEP-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~2.17 h`), awaits human freeze & execution.
2. [`P5-ADD-001.yaml`](../research/protocols/P5-ADD-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.60 h`), awaits human freeze & execution.
3. [`P5-NEURO-001.yaml`](../research/protocols/P5-NEURO-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~0.68 h`), awaits human freeze & execution.
4. [`P5-PHARMA-001.yaml`](../research/protocols/P5-PHARMA-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.54 h`), awaits human freeze & execution.
5. [`P5-STRESS-001.yaml`](../research/protocols/P5-STRESS-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.81 h`), awaits human freeze & execution.
