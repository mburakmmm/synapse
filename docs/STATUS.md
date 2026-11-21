# SYNAPSE Project Status

- **Active Phase:** Phase 5A — Pain Module (**`P5-PAIN-001.frozen.yaml` Frozen & Pushed; Executing `120` Confirmatory + `36` Robustness Runs**); Phases 0–4 Complete
- **Last Updated:** 2026-11-21
- **Environment:** Windows 11 CPU + Docker `29.9.3` (`linux/x86_64`), Python `3.12.11`, `brian2 2.10.1`, Node `v26.0.0`, `graphifyy` (dev tool)

## Verified Gates (Phase 0 – Phase 5A)

| Check | Outcome | Evidence / Observed Metrics |
|---|---|---|
| Phases 0–4 (`flywire_fafb_v630`, `SHIU2024`, Lab, `MET-001`) | Passed | `SHIU2024` `90/90` passed; `P4-MET-001` frozen confirmatory `180/180` + robustness `36/36` passed |
| Linux CI `mypy` Portability Fix | Passed | Guarded `CREATE_NEW_PROCESS_GROUP` (`job_control.py`, `executor.py`); `mypy --platform linux` 0 errors |
| Phase 5A Core Extensions (`EdgeMaskModulation`, `windows.py`) | Passed | Pathway-specific edge masking + pre/stim/post persistence tests (`test_edge_mask_and_windows.py`) |
| Phase 5A Pain Pilot (`P5-PAIN-001-PILOT`, `malecns_v1_0`, `N=3`) | Complete | `24/24` runs (`1507.23 s`, `0` failed, sham `0` spikes); `523539` `40 Hz` stim `18.0 -> 51.3 Hz` (`edge_mask`), `43.3 Hz` (`cell_death`), `16.7 Hz` (`matched_ctrl`) |

## Scientific Scope & Limitations

- **Research Use Only (`RUO`):** Exploratory VNC disinhibition findings are conditional on `malecns_v1_0` connectivity and L1 `synapse_lif_v1`; `malecns_v1_0` lacks `ppk`/`TrpA1` nociceptor subtype tags and gap junctions.
- **Preprint Separation:** `Jones et al. (2025)` (`doi:10.1101/2025.10.28.684868`) is a non-peer-reviewed bioRxiv preprint used solely for anatomical circuit framing.

## Next 1–3 Tasks

1. **Execute Frozen Confirmatory [`P5-PAIN-001.frozen.yaml`](../research/protocols/P5-PAIN-001.frozen.yaml) (`120` runs, `N=15`) & Robustness (`36` runs):** Publish confirmatory findings and reports.
2. **Phase 5B — Sleep / Addiction Planning (`AGENTS.md` §10, §15):** Begin only after Pain confirmatory gate closes.

## Authoritative References

- Contract & Decisions: [AGENTS.md](../AGENTS.md), [ADR-0006](adr/ADR-0006-phase5-pain-vnc-disinhibition.md), [operations_and_backup.md](security/operations_and_backup.md)
- Pain Module: [README.md](../research/modules/pain/README.md), [evidence_register.md](../research/modules/pain/evidence_register.md), [pilot_report.md](../research/modules/pain/pilot_report.md)
- Prior Modules: [shiu2024_reproduction_report.md](validation/shiu2024_reproduction_report.md), [confirmatory_report.md](../research/modules/metabolic/confirmatory_report.md)
