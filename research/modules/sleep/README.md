# Sleep & Circadian Module (`sleep`)

- **UI / Gate Status:** `experimental` (Phase 5B **L3 circadian-homeostatic gates verified** and **L1 exploratory pilot `24/24` completed** on `malecns_v1_0`; confirmatory freeze of [`P5-SLEEP-001.yaml`](../../protocols/P5-SLEEP-001.yaml) pending explicit human approval; modeled quiescence and LIF firing rates are computational proxies, **not** validated behavioral sleep; `RUO`).
- **Organism & Specimen:** Adult male *Drosophila melanogaster* whole CNS (`malecns_v1_0`, `211,577` bodies, `26,028,386` edges; separate male specimen — never pooled with female FlyWire).

## Scope & Key Findings (`P5-SLEEP-001`)

- **Stage 1 — Verified L3 Circadian-Homeostatic Oscillator (`leloup_goldbeter_1998_two_process_v1`):**
  - Integrates the 10-ODE `PER/TIM` circadian molecular clock (`BIOMD0000000021`, `Leloup & Goldbeter, 1998`) coupled to normalized Process `S` hysteresis (`tau_i = 8.76 h`, `tau_d = 9.51 h`, `Abhilash & Shafer, 2024`).
  - All 4 mandatory pre-shift-work verification gates passed (`tau_DD = 24.1346 h`, convergence diff `0.0 h`, `tau_LD = 24.0171 h`, `CT 15` delay `-2.3591 h`, `CT 21` advance `+2.3431 h`, 12 h deprivation rebound `+0.1625` quiescence-rest fraction).
  - Gated 16-day shift-work runs showed re-entrainment in `2.206 d` (`+8 h` delay, peak error `5.793 h`) and `2.641 d` (`-6 h` advance, peak error `7.303 h`), whereas 3-day rotating `+8 h` shifts peaked at `10.814 h` error without continuous re-entrainment (`days_to_reentrain = null`).
- **Stage 2 — Coupled L1 Whole-CNS Exploratory Pilot (`P5-SLEEP-001-PILOT`, `N = 3`, `24/24` runs):**
  - Tested `MeTu2a` (`70` `ACH`) + `aMe12` (`6` `ACH`) light drive alongside dorsal clock `DN1p` (`12` `GLUT`) activation, `12` structurally matched `cb_intrinsic` `GLUT` controls (`|SMD| <= 0.0304`, `0` direct edges to readouts), `EdgeMaskModulation`, `ER5` outgoing efficacy gain (`1.5x`), and `50 Hz` misaligned light + debt probes (`0` sham spikes across `3/3` seeds).
  - Bilateral `TuTuB_b` interneurons (`22794`, `520699`) were selectively suppressed by `DN1p` (`102.083 -> 89.167 Hz` and `100.417 -> 89.167 Hz`), left unaffected by matched controls (`101.667 / 101.250 Hz`), and rescued (`101.667 / 101.250 Hz`) by masking `DN1pB -> TuBu01/TuTuB_b` edges; `50 Hz` misaligned drive recruited downstream `TuBu01` (`114115: +14.583 Hz`), `ExR1` (`11886: +2.917 Hz`), and `ER5` (`10043: +2.083 Hz`).

## Artifacts

- Exploratory & L3 Verification Report: [`pilot_report.md`](pilot_report.md)
- Target & Matched Control Set: [`sleep001_malecns_v1_targets.json`](target_sets/sleep001_malecns_v1_targets.json)
- Literature, Model & ADR Docs: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md), [`ADR-0007`](../../../docs/adr/ADR-0007-phase5b-sleep-circadian-homeostatic-coupling.md)
- Protocols: [`P5-SLEEP-001-pilot.yaml`](../../protocols/P5-SLEEP-001-pilot.yaml) (`draft` exploratory), [`P5-SLEEP-001.yaml`](../../protocols/P5-SLEEP-001.yaml) (`draft` confirmatory — unfrozen pending approval)
