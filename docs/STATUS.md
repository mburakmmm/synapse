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
| **Phase 5C-3 (`Stress`)** | Declared fly stress signaling circuitry | **Planned** | Gated on module evidence register and target validation (`AGENTS.md` §1, §2) |

## Phase 5C-2 Pharma Summary (`P5-PHARMA-001-PILOT`, RUO)

- **L2 Kinetics (`receptor_conductance_modulation_v1`):** `5/5` gates passed with `named_compound_gate_enabled=False` ([ADR-0010](adr/ADR-0010-phase5c-pharma-receptor-conductance-modulation.md)); root-solved Schild slope `1.000000` ($R^2 = 1.0$), bidirectional `Rdl` scale (`0.0–2.0x`), Bliss identity verified.
- **L1 Pilot (`24/24` runs on `malecns_v1_0`, `N=3`, `sham=0`):** `523539` vehicle `14.444 Hz` rose to `35.556 Hz` (`+21.111 Hz`) under `Rdl` `100%` block and fell to `9.444 Hz` under `1.75x` PAM, `6.667 Hz` under `nAChR` `50%` attenuation, and `3.333 Hz` combined (`76.92%` observed vs `69.82%` Bliss null); matched VNC `GABA` control remained `13.889 Hz` (`-0.556 Hz`).

## Deferred Confirmatory Queue (User Reminder — Unfrozen Drafts)

1. [`P5-SLEEP-001.yaml`](../research/protocols/P5-SLEEP-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~2.17 h`), awaits human freeze & execution.
2. [`P5-ADD-001.yaml`](../research/protocols/P5-ADD-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.60 h`), awaits human freeze & execution.
3. [`P5-NEURO-001.yaml`](../research/protocols/P5-NEURO-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~0.68 h`), awaits human freeze & execution.
4. [`P5-PHARMA-001.yaml`](../research/protocols/P5-PHARMA-001.yaml) — `status: draft`, `N=15`, `120` runs (`workers=3` est. `~1.54 h`), awaits human freeze & execution.
