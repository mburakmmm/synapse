# SYNAPSE Project Status

- **Active Phase:** Phase 4 — First Investigation: Metabolic (**Confirmatory `P4-MET-001` + Robustness Complete**); Phase 5 — Module Expansion: Pain / Sleep / Addiction (**Next**)
- **Last Updated:** 2026-11-20
- **Environment:** Windows 11 CPU + Docker `29.9.3` (`linux/x86_64`), Python `3.12.11`, `brian2 2.10.1`, Node `v26.0.0`, `graphifyy` (dev tool)

## Verified Gates (Phase 0 – Phase 4)

| Check | Outcome | Evidence / Observed Metrics |
|---|---|---|
| Phase 0–2 Foundation & Reproduction | Passed | `flywire_fafb_v630` & `malecns_v1_0` verified; `SHIU2024` `90/90` passed (`MN9_right` `68.833 ± 4.243 Hz`) |
| Phase 3 Lab Stack + Docker/PostgreSQL | Passed | Healthy `postgres`/`api`/`worker`/`web`; PostgreSQL `SKIP LOCKED` jobs & `pg_dump`/`pg_restore` verified |
| Phase 4 Confirmatory `P4-MET-001` (`N=30`, frozen) | Passed | `180/180` runs (`3449.42 s`, `0` failed, sham `0` spikes); `MN9_right` `1.50x` Δ `+30.900 Hz`, specificity Δ `+30.900 Hz`, $q=9.999\times 10^{-5}$ |
| Phase 4 Robustness & Sensitivity (`N=6` arms) | Complete | `36/36` runs (`811.89 s`); positive `1.50x` Δ holds in `synapse_lif_v1` (`+34.667 Hz`) & `±10% w_syn_v` (`+31.500`/`+23.500 Hz`) |
| MaleCNS Structural Check (`malecns_v1_0`) | Audited | `MN9` (`16949`/`10331`) + `60` `tpGRN` found; `0` sugar-GRN tags -> cross-specimen run deferred per integrity rules |

## Scientific Scope & Limitations

- **Computational Investigation Only (`RUO`):** Confirmatory simulation & robustness do not substitute for wet-lab biological validation or human clinical claims.
- **L1 Model Constraints:** Zero spontaneous noise leaves un-driven matched controls silent (`0.000 Hz`); baseline firing rate depends sharply on global `w_syn_v` (`4.500–38.833 Hz`). `brian2_cuda` remains unverified (`verified=false`).

## Next 1–3 Tasks

1. **Human Review of [`confirmatory_report.md`](../research/modules/metabolic/confirmatory_report.md) & [`met001_outline.md`](../research/manuscripts/met001_outline.md):** Complete CRediT authorship and decide archival/DOI scope (`Zenodo`/preprint requires explicit approval).
2. **Phase 5 — Pain Module Gate (`AGENTS.md` §10, §15):** Review Khuong et al. (`10.1126/sciadv.aaw4099`) & adult nociceptive connectivity before scoping inhibitory-disruption protocols.

## Authoritative References

- Contract & Ops: [AGENTS.md](../AGENTS.md), [operations_and_backup.md](security/operations_and_backup.md)
- Decisions & Validation: [ADR-0004](adr/ADR-0004-shiu2024-reproduction-fidelity.md), [ADR-0005](adr/ADR-0005-phase3-research-laboratory-architecture.md), [shiu2024_reproduction_report.md](validation/shiu2024_reproduction_report.md)
- Metabolic Reports: [README.md](../research/modules/metabolic/README.md), [pilot_report.md](../research/modules/metabolic/pilot_report.md), [confirmatory_report.md](../research/modules/metabolic/confirmatory_report.md)
