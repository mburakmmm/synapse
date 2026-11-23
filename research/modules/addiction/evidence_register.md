# Evidence Register: `addiction` (`P5-ADD-001`)

> **Research Use Only (RUO):** All L2 equations, conditioning schedules, and L1 `malecns_v1_0` cohorts trace exclusively to peer-reviewed *Drosophila* neuroscience publications (`peer_review_status: peer_reviewed`) and curated local connectome tables. Outputs are strictly *Drosophila* cue-conditioning proxies (`PI`, `MBON` firing rates), never clinical dependence or human translational claims (`AGENTS.md` §1, §2, §10).

## Verified Peer-Reviewed Literature (`research/literature/source_register.yaml`)

| Ref ID | Citation & Identifiers | Review Status | Role in `P5-ADD-001` |
|---|---|---|---|
| `aso2014_elife` | Aso Y et al. (2014), *eLife* 3:e04580 · DOI: [`10.7554/eLife.04580`](https://doi.org/10.7554/eLife.04580) · PMID `25535794` · PMCID `PMC4273436` | Peer-reviewed | Establishes compartmental tiling and valence segregation across `GLUT` avoidance vs. `ACH`/`GABA` approach MBONs. |
| `owald2015_neuron` | Owald D et al. (2015), *Neuron* 86(2):417–427 · DOI: [`10.1016/j.neuron.2015.03.025`](https://doi.org/10.1016/j.neuron.2015.03.025) · PMID `25864636` · PMCID `PMC4416108` | Peer-reviewed | Demonstrates glutamatergic horizontal-lobe MBONs (`M4/6`, incl. `MBON02`) drive avoidance and undergo reward learning depression. |
| `hige2015_neuron` | Hige T et al. (2015), *Neuron* 88(5):985–998 · DOI: [`10.1016/j.neuron.2015.11.003`](https://doi.org/10.1016/j.neuron.2015.11.003) · PMID `26637800` · PMCID `PMC4674068` | Peer-reviewed | Establishes compartment-specific heterosynaptic `KC -> MBON` LTD triggered by coincident KC activity and DAN reinforcement. |
| `cohn2015_cell` | Cohn R et al. (2015), *Cell* 163(7):1742–1755 · DOI: [`10.1016/j.cell.2015.11.019`](https://doi.org/10.1016/j.cell.2015.11.019) · PMID `26687359` | Peer-reviewed | Documents coordinated opponent dopaminergic modulation across mushroom body compartments. |
| `felsenberg2017_nature` | Felsenberg J et al. (2017), *Nature* 544:240–244 · DOI: [`10.1038/nature21716`](https://doi.org/10.1038/nature21716) · PMID `28379939` | Peer-reviewed | Shows re-evaluation of learned odor memory recruits recurrent `MBON -> DAN` feedback loops. |
| `felsenberg2018_cell` | Felsenberg J et al. (2018), *Cell* 175(3):709–722.e15 · DOI: [`10.1016/j.cell.2018.08.021`](https://doi.org/10.1016/j.cell.2018.08.021) · PMID `30245010` · PMCID `PMC6198041` | Peer-reviewed | Proves reward memory extinction recruits parallel opposing `PPL1 -> MBON` depression while leaving the original `PAM` trace intact. |
| `handler2019_cell` | Handler A et al. (2019), *Cell* 178(1):60–75.e19 · DOI: [`10.1016/j.cell.2019.05.040`](https://doi.org/10.1016/j.cell.2019.05.040) · PMID `31230716` · PMCID `PMC9012144` | Peer-reviewed | Establishes `Dop1R1` depression vs. `Dop1R2` potentiation receptor pathways and ~4 s KC eligibility timing constants. |
| `li2020_elife` | Li F et al. (2020), *eLife* 9:e62576 · DOI: [`10.7554/eLife.62576`](https://doi.org/10.7554/eLife.62576) · PMID `33315010` | Peer-reviewed | Adult *Drosophila* MB EM connectome resolving `ALPN -> KC -> MBON` and cross-compartment `MBON -> MBON` edges. |
| `scaplen2020_elife` | Scaplen KM et al. (2020), *eLife* 9:e48730 · DOI: [`10.7554/eLife.48730`](https://doi.org/10.7554/eLife.48730) · PMID `32497004` | Peer-reviewed | Maps *Drosophila* mushroom body dopaminergic/output circuitry mediating conditioned alcohol-associated odor preference. |
| `gkanias2022_elife` | Gkanias E et al. (2022), *eLife* 11:e75611 · DOI: [`10.7554/eLife.75611`](https://doi.org/10.7554/eLife.75611) · PMID `35363138` · PMCID `PMC8975552` | Peer-reviewed | Minimal continuous-time incentive-circuit ODE model capturing acquisition, extinction, and recovery in MB motifs. |
| `kaun2011_natneurosci` | Kaun KR et al. (2011), *Nat Neurosci* 14(5):612–619 · DOI: [`10.1038/nn.2805`](https://doi.org/10.1038/nn.2805) · PMID `21499254` | Peer-reviewed | Conditioned odor preference paradigm for intoxicating ethanol reward in flies (behavioral proxy, not human dependence). |
| `lin2014_natneurosci` | Lin AC et al. (2014), *Nat Neurosci* 17(4):559–568 · DOI: [`10.1038/nn.3660`](https://doi.org/10.1038/nn.3660) · PMID `24561998` · PMCID `PMC4000970` | Peer-reviewed | `APL` GABAergic global/recurrent inhibition preserves sparse odor coding across Kenyon cells. |
| `amin2020_elife` | Amin H et al. (2020), *eLife* 9:e56954 · DOI: [`10.7554/eLife.56954`](https://doi.org/10.7554/eLife.56954) · PMID `32955437` | Peer-reviewed | Compartmentalized electrotonic inhibition by `APL` in MB processes (explains point-neuron somatic over-inhibition). |

## Quantitative Correspondence in `malecns_v1_0` (`add001_malecns_v1_targets.json`)

- **Specimen:** Adult male CNS `malecns_v1_0` (`211,577` bodies, `26,028,386` edges; manifest `6df05f9f76e98e55f5e4f13e195ebd604ec41c644751c47a79f9855a92d5f496`, graph `ef5324051bbaaf960cc12754f1017b14700dc725c2c85e5afce75fb5a45256ce`; never pooled with female FlyWire).
- **Disjoint Sparse KC Cohorts:**
  - `cs_plus_kcs` (`143` `DM1_lPN + DM4_adPN`-selective KCs): `1,108` synapses to `MBON02/04` (`avoid`) and `2,863` synapses to `MBON12/14/18` (`approach`).
  - `matched_ctrl_kcs` (`143` exact `(cell_type, soma_side)` Hungarian-matched unresponsive KCs): `0` synapses from `PN_A`, `0` synapses from `PN_B`, `1,187` synapses to `MBON02/04`, `2,720` synapses to `MBON12/14/18`, with `max|SMD| = 0.13225` across all 6 structural features (`out_deg = -0.01207`, `out_syn = -0.01599`, `in_deg = -0.02404`, `in_syn = +0.13225`, `syn_avoid = -0.12311`, `syn_appr = +0.11860`).
  - `cs_minus_kcs` (`143` disjoint `DC1_adPN + VA2_adPN`-selective KCs): `1,525` synapses to `MBON02/04` and `3,744` synapses to `MBON12/14/18`.
- **Cross-Compartment & Local Inhibition Architecture:** `MBON02 (GLUT) -> MBON14 (ACH)` comprises `380` synapses; `APL (GABA)` sends `818`, `1,162`, and `441` synapses onto `MBON01`, `MBON05`, and `MBON11`, vs. only `96` onto `MBON02` and `78` onto `MBON14`.

## Declared Evidence & Model Gaps (`AGENTS.md` §2, §10)

1. **Zero Direct Monoamine Weight in L1:** Under `synapse_lif_v1`, `PAM` (`316` `DA`), `PPL1` (`16` `DA`), `DPM` (`2` `DA`), `OCT`, and `SER` carry `0.0` fast synaptic conductance weight (`unknown_nt_policy = "zero_effect"`); reinforcement modulation is therefore mediated explicitly via L2 `mb_dopamine_plasticity_v1` snapshots applied as `EdgeMaskModulation`.
2. **Somatic Point-Neuron `APL` & Full-CNS Recurrent Dynamics:** In single-compartment LIF neurons, dense `APL` GABAergic synapses onto `MBON01/05/11` (`441–1,162` vs. `78–96` on `MBON02/14`) clamp `MBON01/05/11` to `0.0 Hz` during the early feedforward window (`[0.1, 0.2) s`), while lack of localized `APL` dendritic compartmentalization (`Amin et al. 2020`) permits sustained `35 Hz` `CS+` KC drive to recruit a brain-wide cholinergic `MBON12/14/18 -> CRE011/LH/SMP -> KCab` recurrent cascade across `[0.2, 0.6] s`. Both windows (`[0.1, 0.2) s` vs. `[0.2, 0.6] s`) are therefore reported transparently.
3. **Behavioral Proxy Only:** Neither L2 `PI` nor L1 MBON firing constitutes clinical addiction, tolerance, withdrawal, or human drug efficacy.
