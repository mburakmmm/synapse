# Addiction & Reward Learning Module (`addiction`)

- **UI / Gate Status:** `experimental` (Phase 5B **L2 three-factor MB plasticity gates verified `5/5`** and **L1 exploratory pilot `24/24` completed** on `malecns_v1_0`; confirmatory freeze of [`P5-ADD-001.yaml`](../../protocols/P5-ADD-001.yaml) pending explicit human approval; learned preference index `PI` and LIF firing rates are computational *Drosophila* cue-conditioning proxies, **not** clinical human dependence, craving, or diagnosis; `RUO`).
- **Organism & Specimen:** Adult male *Drosophila melanogaster* whole CNS (`malecns_v1_0`, `211,577` bodies, `26,028,386` edges; separate male specimen — never pooled with female FlyWire).

## Scope & Key Findings (`P5-ADD-001`)

- **Stage 1 — Verified L2 MB Three-Factor Dopamine Plasticity (`mb_dopamine_plasticity_v1`):**
  - Integrates presynaptic KC eligibility traces (`tau_e_s = 4.0 s`), reward `PAM` dopamine transients (`tau_d_s = 1.5 s`), and unreinforced `CS+` prediction-error `PPL1` transients (`omission_gain = 1.2`) across opposing compartments (`w_avoid` on glutamatergic `MBON02/04`; `w_appr` on cholinergic `MBON12/14/18`; `g_cross = 0.25` cross-compartment inhibition).
  - All 5 mandatory gates passed (`dt/2` convergence `max|dW| = 1.947e-4`; acquisition `PI = +0.33123`, `w_avoid(CS+) = 0.292978`, `|w_avoid(CS-) - 1.0| = 0.0`; parallel extinction `PI = +0.045171` while preserving `w_avoid(CS+) = 0.334152`; reinstatement `PI = +0.26580`, `w_appr(CS+) = 0.924609` exceeding passive spontaneous recovery `+0.16480`; `sham = 0.0`, `yoked_unpaired = 6.2e-5`, `dan_blocked = 0.0`).
- **Stage 2 — Coupled L1 Whole-CNS Exploratory Pilot (`P5-ADD-001-PILOT`, `N = 3`, `24/24` runs):**
  - Drove `143` sparse `CS+` KCs vs. `143` `CS-` KCs and compared against `143` exact `(cell_type, soma_side)` Hungarian-matched unresponsive control KCs (`|SMD| <= 0.13225`, `0` PN synapses) and `sham_zero_stimulus` (`0` spikes across `3/3` seeds).
  - Early feedforward window (`[0.1, 0.2) s`): acquisition eliminated `MBON02_L` (`522749`: `26.67 -> 0.00 Hz`, early L1 valence `-0.0959 -> +1.0000`) while matched controls kept `26.67 Hz` (`-0.0959`) and `CS-` remained unchanged (`63.33 -> 63.33 Hz`).
  - Full stimulus / trial readout (`[0.0, 0.6] s`, recruiting a full-CNS `MBON12/14/18 -> CRE011 -> KCab` recurrent excitation cascade across `[0.2, 0.6] s`): acquisition increased `MBON14_R` (`17946`: `+71.111 Hz`), extinction collapsed `MBON14_R` (`-193.333 Hz`), `MBON18_R` (`-176.111 Hz`), and `MBON12_L` (`-174.444 Hz`), reinstatement restored `MBON14_R` (`+178.889 Hz`) and `MBON18_R` (`+162.222 Hz`), while matched-control (`-0.556 Hz`) and `CS-` (`+0.000 Hz`) controls stayed null.

## Artifacts

- Exploratory & L2 Verification Report: [`pilot_report.md`](pilot_report.md)
- Target & Matched Control Set: [`add001_malecns_v1_targets.json`](target_sets/add001_malecns_v1_targets.json)
- Literature, Model & ADR Docs: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md), [`ADR-0008`](../../../docs/adr/ADR-0008-phase5b-addiction-mb-plasticity-coupling.md)
- Protocols: [`P5-ADD-001-pilot.yaml`](../../protocols/P5-ADD-001-pilot.yaml) (`draft` exploratory), [`P5-ADD-001.yaml`](../../protocols/P5-ADD-001.yaml) (`draft` confirmatory — unfrozen pending approval)
