# Pain Research Module (`pain`)

- **UI / Gate Status:** `experimental` (Phase 5A exploratory pilot completed on `malecns_v1_0`; confirmatory protocol [`P5-PAIN-001.yaml`](../../protocols/P5-PAIN-001.yaml) drafted & awaiting human approval/freeze; biological wet-lab validation not claimed; `RUO`).
- **Organism & Specimen:** Adult male *Drosophila melanogaster* whole CNS (`malecns_v1_0`, `211,577` bodies, `26,028,386` edges; separate male specimen — never pooled with female FlyWire).

## Scope & Exploratory Findings (`P5-PAIN-001-PILOT`)

- Models **acute VNC GABAergic disinhibition (`EdgeMaskModulation`) vs. partial attenuation (`50%`) vs. GABAergic silencing (`NeuronSilencing`, cell-death proxy)** driven by top `30` right-side middle-leg (`MesoLN`) mechanosensory afferents, contrasted against sham (`0` spikes) and `26` degree/synapse/NT-matched VNC `GABA` controls (`|SMD| <= 0.0970`).
- **Key Exploratory Observation (`N = 3`, `24/24` runs):** Pathway-selective `acute_edge_mask` elevated ascending output (`523539 ANXXX027_L`: `18.0 -> 51.3 Hz` stim window; `558778 AN08B012_R`: `20.7 -> 28.0 Hz`; `10592 AN08B012_L`: `15.3 -> 17.3 Hz`), whereas global `gaba_cell_death` selectively amplified `523539` (`43.3 Hz`, `+25.3 Hz` stim / `+15.833 Hz` full trial) vs. matched controls (`16.7 Hz` stim) while decreasing `10592` (`9.3 Hz`), demonstrating circuit-dependent intra-VNC redistribution.
- **Next Required Gate (`AGENTS.md` §8, §15):** Human review and explicit confirmation (`synapse protocol freeze research/protocols/P5-PAIN-001.yaml --confirm-freeze`) prior to executing confirmatory `N = 15` runs.

## Artifacts

- Target & Matched Control Set: [`pain001_malecns_v1_targets.json`](target_sets/pain001_malecns_v1_targets.json)
- Literature & Model Docs: [`evidence_register.md`](evidence_register.md), [`model_card.md`](model_card.md), [`pilot_report.md`](pilot_report.md)
- Protocols: [`P5-PAIN-001-pilot.yaml`](../../protocols/P5-PAIN-001-pilot.yaml) (`exploratory`), [`P5-PAIN-001.yaml`](../../protocols/P5-PAIN-001.yaml) (`confirmatory`, `status: draft`)
