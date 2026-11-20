# Metabolic Evidence Register & Proxy Assumptions

> **RUO Notice:** Citations below anchor qualitative biological mechanisms in *Drosophila melanogaster*; SYNAPSE parameters are reduced computational proxies, not biophysically measured conductances.

## Literature Mapping (`2026-11-20`)

| Source ID | Reference | Biological Observation | Modeling Representation & Gap |
|---|---|---|---|
| `inagaki2012_cell` | Inagaki et al., *Cell* 2012 (`10.1016/j.cell.2011.12.022`) | Nutritional deprivation elevates dopaminergic signaling onto sugar GRNs, increasing sensory gain and appetitive responsiveness. | Represented in L1 `shiu2024_lif` as a static `EdgeGainModulation(scope="outgoing", factor>1)` proxy on sugar GRNs; intracellular cAMP/DopEcR/GPCR kinetics are omitted. |
| `marella2012_neuron` | Marella, Mann & Scott, *Neuron* 2012 (`10.1016/j.neuron.2011.12.032`) | Specific dopaminergic neurons gate sucrose proboscis extension reflex (PER) threshold. | Output proxy uses `MN9` firing rate under sub-maximal `50 Hz` sugar GRN drive; behavioral PER probability curves are not modeled directly. |
| `engert2022_elife` | Engert, Sterne, Bock & Scott, *eLife* 2022 (`10.7554/eLife.78110`) | Gustatory receptor neuron projections segregate anatomically by taste modality and downstream connectivity in adult EM data. | Justifies isolating the 21 right-hemisphere sugar GRNs and excluding 1-hop postsynaptic targets from structurally matched controls (`met001_flywire_v630_targets.json`). |
| `munch2022_nature` | Münch, Goldschmidt & Ribeiro, *Nature* 2022 (`10.1038/s41586-022-04909-5`) | Internal nutrient state reshapes feeding sensorimotor choice probabilities at circuit level. | Motivates testing circuit specificity via structurally matched non-gustatory controls rather than equating any global weight increase with hunger. |

## Explicit Gaps Remaining

- No IPC/DILP, AKH, sNPF, or endocrine feedback loops (deferred to L2/L3 extensions).
- `flywire_fafb_v630` encodes sign-only transmitter predictions (`EXCITATORY_SIGN`), not cholinergic receptor subtypes or neuromodulator receptor expression.
