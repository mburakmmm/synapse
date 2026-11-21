# Pain Research Module (`pain`)

- **UI / Gate Status:** `confirmatory_simulation_complete` (Phase 5A frozen confirmatory `120/120` runs + `36/36` exploratory robustness runs completed on `malecns_v1_0`; computational outcomes conditional on LIF equations — biological wet-lab validation is *not* claimed; `RUO`).
- **Organism & Specimen:** Adult male *Drosophila melanogaster* whole CNS (`malecns_v1_0`, `211,577` bodies, `26,028,386` edges; separate male specimen — never pooled with female FlyWire).

## Scope & Key Findings (`P5-PAIN-001`)

- Models **acute VNC GABAergic disinhibition (`EdgeMaskModulation`) vs. partial attenuation (`50%`) vs. global GABAergic silencing (`NeuronSilencing`, cell-death proxy)** driven by top `30` right-side middle-leg (`R-MesoLN`) mechanosensory afferents, contrasted against `sham_zero_stimulus` (`0` spikes across `15/15` runs) and `26` degree/synapse/NT-matched VNC `GABA` controls (`|SMD| <= 0.0970`).
- **Frozen Confirmatory Outcome (`N = 15`, `120/120` runs, [`P5-PAIN-001.frozen.yaml`](../../protocols/P5-PAIN-001.frozen.yaml)):** All `6` primary full-trial contrasts passed BH-FDR (`q = 9.9990e-05`): `acute_edge_mask` elevated `523539` (`ANXXX027_L`) by `+20.667 Hz` vs. baseline (`11.917 -> 32.583 Hz`) and `+20.667 Hz` vs. matched control, while `558778` (`AN08B012_R`) increased by `+3.833 Hz` vs. baseline (`13.500 -> 17.333 Hz`) and `+3.333 Hz` vs. matched control (`[0.1, 0.6) s` stim window: `523539` `19.067 -> 51.467 Hz`).
- **Circuit-Dependent Mechanism Dissociation:** Matched-control ablation produced null shifts (`523539` `0.000 Hz`, `p = 1.0000`; `558778` `+0.500 Hz`, `p = 0.3544`), whereas global `gaba_cell_death` selectively depressed `10592` (`AN08B012_L`, `-4.500 Hz`, `p = 2.9997e-04`) compared to pathway-selective `acute_edge_mask` (`+1.417 Hz`, `p = 0.0213`).
- **Exploratory Robustness (`N = 6`, `36/36` runs):** Positive `acute_edge_mask` amplification persisted on `523539` (`+15.208` to `+20.833 Hz`, exact `p = 0.03125`) and `558778` (`+2.708` to `+3.750 Hz`, `p = 0.03125`) across `shiu2024_lif` (`linear` solver) and `±10%` `w_syn_v` perturbations (`0.2475` / `0.3025 mV`).

## Artifacts

- Confirmatory & Exploratory Reports: [`confirmatory_report.md`](confirmatory_report.md), [`pilot_report.md`](pilot_report.md)
- Target & Matched Control Set: [`pain001_malecns_v1_targets.json`](target_sets/pain001_malecns_v1_targets.json)
- Literature, Model & ADR Docs: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md), [`ADR-0006`](../../../docs/adr/ADR-0006-phase5-pain-vnc-disinhibition.md)
- Protocols: [`P5-PAIN-001.frozen.yaml`](../../protocols/P5-PAIN-001.frozen.yaml) (`frozen`), [`P5-PAIN-001.yaml`](../../protocols/P5-PAIN-001.yaml) (`approved`), [`P5-PAIN-001-pilot.yaml`](../../protocols/P5-PAIN-001-pilot.yaml), robustness drafts (`P5-PAIN-001-robust-*.yaml`)
