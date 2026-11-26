# Working Manuscript Outline: `PAIN-001` Adult Male VNC GABAergic Disinhibition vs. Cell Death

> **DRAFT MANUSCRIPT PACKAGE (`AGENTS.md` §12):** Every quantitative value below traces directly to verified on-disk artifacts (`P5-PAIN-001.frozen.yaml`, [`confirmatory_report.md`](../modules/pain/confirmatory_report.md)). Authorship, CRediT roles, conflict declarations, funding, ethics determination, and external publication require explicit human review and approval.

## 1. Research Scope & Non-Clinical Disclaimer

- **Organism & Specimen:** Adult male *Drosophila melanogaster* central nervous system (`malecns_v1_0`, `v1.0`, `manifest_sha256: 6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`, `211,577` bodies, `26,028,386` edges; strictly never pooled with female FlyWire IDs).
- **Model Scope:** Reduced L1 LIF (`synapse_lif_v1`, `brian2_cpu`, `exact`, `w_syn_v = 0.000275 V`, `unknown_nt_policy = zero_effect`, **Research Use Only**). Outcomes are modeled ascending relay firing rates, **not** human pain scores, clinical neuropathy, or analgesic efficacy.

## 2. Literature Grounding & Preprint Flagging

- Grounded in `khuong2019_sciadv` (`10.1126/sciadv.aaw4099`) and `cheong2026_elife` (`10.7554/eLife.96084`) in [`source_register.yaml`](../literature/source_register.yaml).
- **Mandatory Preprint Disclosure:** Candidate thermal ascending validation reference `jones2025_biorxiv` (`10.1101/2025.10.28.684868`) is explicitly tagged `preprint_not_peer_reviewed` and is not cited as peer-reviewed biological validation.

## 3. Methods (`P5-PAIN-001.frozen.yaml`, `a379c7e1c7b2...`)

- **Targets & Matched Controls ([`pain001_malecns_v1_targets.json`](../modules/pain/target_sets/pain001_malecns_v1_targets.json)):** `30` right `MesoLN` mechanosensory `ACH` afferents, `26` feedforward VNC `GABA` interneurons, and `26` Hungarian-matched non-target VNC `GABA` controls (`|SMD| <= 0.0970`, `0` direct edges onto `ascending_readout_all`).
- **Locked Confirmatory Execution:** `8` conditions × `15` paired seeds (`master = 20261131`, `120/120` succeeded, `0` failed, `8271.70 s` wall, commit `5a878cdd72cee9823f708c76d4058488f7051577`, `git_dirty = false`).

## 4. Primary Confirmatory & Mechanistic Dissociation Results (`0.0–0.8 s`, `N = 15`)

- **Controls:** `sham_zero_stimulus` emitted `0` spikes (`15/15` seeds). Silencing matched VNC `GABA` controls produced null shifts on `523539` (`Δ = 0.000 ± 2.004 Hz`, `p = 1.0000`) and `558778` (`Δ = +0.500 ± 1.623 Hz`, `p = 0.3544`).
- **All `6` Primary Contrasts Cleared BH-FDR (`q = 9.9990e-05`):**
  - `523539` (`ANXXX027_L`): `acute_edge_mask` vs. `40hz_baseline` (`32.583` vs `11.917 Hz`) Δ `+20.667 ± 2.907 Hz` (`[+19.331, +22.167]`); vs. matched control `+20.667 ± 2.209 Hz`. `gaba_cell_death` vs. baseline `+16.000 ± 2.639 Hz`; vs. control `+16.000 ± 2.175 Hz`.
  - `558778` (`AN08B012_R`): `acute_edge_mask` vs. baseline (`17.333` vs `13.500 Hz`) Δ `+3.833 ± 1.858 Hz`; vs. control `+3.333 ± 1.391 Hz`.
- **Circuit Dissociation (`10592` `AN08B012_L`):** Pathway-selective `acute_edge_mask` raised `10592` (`+1.417 Hz`, `p = 0.0213`), whereas whole-cell `gaba_cell_death` reduced `10592` (`-4.500 Hz`, `p = 2.9997e-04`).
- **Post-Stimulus Persistence:** `[0.6, 0.8] s` tail remained `<= 1.667 Hz` (`<= 10.76 ms`), consistent with `tau_syn = 5 ms` without intrinsic rebound currents.
- **Figure Source Bundles:** `runs/phase5_pain001_confirmatory/bundle_p1_523539_edge_mask` and companion confirmatory bundles.

## 5. Governance Placeholders (`[HUMAN AUTHOR INPUT REQUIRED]`)

- **Authors / ORCID / CRediT / Affiliations / Ethics / Funding / AI Disclosure (`Antigravity`):** `[TO BE COMPLETED BY HUMAN AUTHORS BEFORE ARCHIVING OR SUBMISSION]`
