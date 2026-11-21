# Evidence Register: `pain` (`P5-PAIN-001`)

> **Research Use Only (RUO):** Literature evidence anchors adult *Drosophila melanogaster* VNC disinhibition and ascending escape/avoidance anatomy. Preprint findings are explicitly separated from peer-reviewed publications (`AGENTS.md` §3, §10, §12).

## Primary Literature Register (`research/literature/source_register.yaml`)

| Ref ID | Citation & Identifiers | Review Status | Claim Scope & Role in `P5-PAIN-001` |
|---|---|---|---|
| `khuong2019_sciadv` | Khuong TM, Wang QP, Manion J, Oyston LJ, Lau MT, Towler H, Lin YQ, Neely GG (2019), *Science Advances* 5(7):eaaw4099 · DOI: [`10.1126/sciadv.aaw4099`](https://doi.org/10.1126/sciadv.aaw4099) · PMID `31309148` · PMCID `PMC6620091` | Peer-reviewed | Establishes that right middle-leg (`MesoLN` / `T2`) nerve amputation triggers `nAChRα1`-dependent caspase death of VNC GABAergic interneurons and thermal escape sensitization (`38°C`), and that direct VNC GABA disruption reproduces hypersensitivity without injury. Motivated comparing acute pathway masking (`edge_mask`), `50%` attenuation, and full GABA silencing (`both_zero`). |
| `cheong2026_elife` | Cheong HSJ, Eichler K, Stürner T, Asinof SK, Champion AS, Marin EC, Oram TB, Sumathipala M, Venkatasubramanian L, Namiki S, Siwanowicz I, Costa M, Berg S, FlyEM Project Team, Jefferis GSXE, Card GM (2026), *eLife* · DOI: [`10.7554/eLife.96084`](https://doi.org/10.7554/eLife.96084) · PMID `42474298` · PMCID `PMC13384506` | Peer-reviewed | Establishes VNC hemilineage taxonomy, descending commands (`DNp01` Giant Fiber, `DNp02`, `DNp04`, `DNp06`, `DNp11`, `MDN`), and jump motor neurons (`TTMn`) in the Male Adult Nerve Cord (`MANC` / `malecns`). |
| `jones2025_biorxiv` | Jones JM, Sustar A, Mamiya A, Walling-Bell S, Chou GM, Cook AP, Tuthill JC (2025-10-29), *bioRxiv* · DOI: [`10.1101/2025.10.28.684868`](https://doi.org/10.1101/2025.10.28.684868) · PMID `41280033` · License `cc_by_nd` | **Non-peer-reviewed preprint** | Reports that adult *Drosophila* abdominal multidendritic (`md`) thermal nociceptors (`>40°C`) connect strongly onto VNC-to-brain ascending interneurons mediating rapid escape and sustained avoidance. Treated strictly as anatomical motivation for recording ascending VNC-to-brain relays (`ANXXX027`, `AN08B012`) alongside motor readout `TTMn`. |

## Quantitative Correspondence in `malecns_v1_0` (`pain001_malecns_v1_targets.json`)

- **Specimen:** Adult male CNS `malecns_v1_0` (`211,577` bodies, `26,028,386` edges, `125,365,933` synapses; `data/curated/malecns_v1_0/`, manifest `6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`, graph `ef5324051bbaaf960cc12754f1017b14700dc725c2c85e5afce75fb5a45256ce`).
- **Afferent Drive (`30` cells):** Top `30` right-side (`rootSide == "R"`) middle-leg (`entryNerve == "MesoLN"`) cholinergic tactile afferents (`vnc_sensory` / `mechanosensory_tactile`, `ACH`) ranked by synapse count onto `AN08B012` (`824` direct synapses onto `AN08B012`, `446` onto `ANXXX027_L` `523539`).
- **Feedforward VNC GABA Targets (`26` cells):** All `vnc_intrinsic` `GABA` interneurons receiving `>= 5` synapses from those `30` afferents (`1,192` summed sensory synapses across top cohort) and forming `>= 10` synapses onto `AN08B012` (`1,390` synapses onto `an08b012_all`; `1,013` onto `anxxx027_pair`), dominated by bilateral `IN13A004`, `IN05B010`, and `IN05B001`.
- **Matched Non-Target Controls (`26` cells):** `26` `vnc_intrinsic` `GABA` cells matched 1-to-1 on `log1p` degrees/synapses excluding all `1-hop` presynaptic partners of all `6` ascending relays (`|SMD| <= 0.0970`, `0` direct synapses to `ascending_readout_all`, only `1` control receiving `17` sensory synapses).

## Declared Evidence & Model Gaps (`AGENTS.md` §2, §10)

1. **No Verified `ppk` / `TrpA1` Nociceptor Subtype Tags in `malecns_v1_0`:** While `receptorType` includes putative `ppk23`/`ppk25`/`IR52b`, explicit `ppk26`/`TrpA1`/`painless` polymodal nociceptor annotations are absent; driven `MesoLN` afferents are annotated cholinergic mechanosensory tactile fibers (`mech_sens_allodynia_proxy`), not verified pure peptidergic/thermal nociceptors.
2. **No Gap Junctions or Slow Neuromodulation (L1 LIF Only):** `malecns_v1_0` connectivity excludes `shakB` electrical synapses (`DNp01 -> TTMn` exhibits `90` chemical synapses alongside unmodeled electrical coupling in vivo), neuropeptides, and `nAChRα1`/`twist`-mediated chronic synaptic plasticity (`L1` captures acute circuit disinhibition vs. synaptic deletion proxy only).
3. **Single Male Specimen:** Findings cannot establish population variance or sex dimorphism across specimens.
