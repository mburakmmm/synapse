# Metabolic Research Module (`metabolic`)

- **Status:** `confirmatory_simulation_complete` (exploratory pilot + frozen confirmatory `P4-MET-001` + robustness arms completed; biological wet-lab validation not claimed; `RUO`)
- **Organism & Dataset:** Adult female *Drosophila melanogaster* (`flywire_fafb_v630`) — non-clinical research only.
- **Prior Reproduction Gate:** Phase 2 `SHIU2024-FEEDING-BENCHMARK` passed (`90/90` runs on `flywire_fafb_v630`).

## Summary of Findings (`MET-001`)

- Under `50 Hz` sucrose drive on `flywire_fafb_v630`, frozen confirmatory simulation (`P4-MET-001.frozen.yaml`, `180/180` runs, `0` failed, `0` sham spikes) showed monotonic `MN9_right` elevation from `20.200 Hz` to `42.200 Hz` (`1.25x`, Δ `+22.000 Hz`) and `51.100 Hz` (`1.50x`, Δ `+30.900 Hz`), exceeding matched non-gustatory controls (`20.200 Hz`, specificity Δ `+30.900 Hz`, BH-FDR $q = 9.999 \times 10^{-5}$).
- Robustness checks confirmed positive `+1.50x` Δ under canonical `synapse_lif_v1` (`+34.667 Hz`) and `±10% w_syn_v` (`+31.500` / `+23.500 Hz`), while noting strong baseline sensitivity to `w_syn_v` (`4.500`–`38.833 Hz`) and zero spontaneous firing noise in L1 LIF.

## Artifacts

- Target & Control Set: [`met001_flywire_v630_targets.json`](target_sets/met001_flywire_v630_targets.json)
- Evidence & Model Cards: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md)
- Protocols: [`P4-MET-001-pilot.yaml`](../../protocols/P4-MET-001-pilot.yaml), [`P4-MET-001.yaml`](../../protocols/P4-MET-001.yaml), [`P4-MET-001.frozen.yaml`](../../protocols/P4-MET-001.frozen.yaml), [`P4-MET-001-robust-canonical-lif.yaml`](../../protocols/P4-MET-001-robust-canonical-lif.yaml), [`P4-MET-001-robust-wsyn-low.yaml`](../../protocols/P4-MET-001-robust-wsyn-low.yaml), [`P4-MET-001-robust-wsyn-high.yaml`](../../protocols/P4-MET-001-robust-wsyn-high.yaml)
- Reports & Manuscript Package: [`pilot_report.md`](pilot_report.md), [`confirmatory_report.md`](confirmatory_report.md), [`met001_outline.md`](../../manuscripts/met001_outline.md)
