# Model Card: `pain` Module (`synapse_lif_v1` on `malecns_v1_0`)

> **Research Use Only (RUO):** Mechanistic L1 connectome-grounded Leaky Integrate-and-Fire simulation on `malecns_v1_0`. Status: `experimental` (exploratory pilot complete; confirmatory protocol awaiting human approval). **Not** validated for biological injury equivalence or human pain physiology.

## 1. Model & Graph Identity

- **Dynamical Model:** `synapse_lif_v1` (`revision: 1.0`, canonical manifest SHA-256 `4938436d7f1a63b2588a48ccbf038927246273cdea3dcca0a43cb269cb1ca8c2` protocol-bound; exact `LIFParameters()` manifest hash verified by `synapse model list --json`)
- **Backend & Numerics:** `brian2_cpu` (`numpy` target, `float64`), `solver="exact"`, `dt = 0.1 ms` (`0.0001 s`), `dg_unless_refractory = false`, `delay = 1.8 ms`, `tau_m = 20 ms`, `tau_syn = 5 ms`, `t_ref = 2.2 ms`, `v_rest = v_reset = -52 mV`, `v_threshold = -45 mV`, `w_syn_v = 0.275 mV`.
- **Neurotransmitter Sign Mapping (`unknown_nt_policy = "zero_effect"`):**
  - `ACH`: `+1.0 * w_syn_v`
  - `GABA`: `-1.0 * w_syn_v`
  - `GLUT`: `-1.0 * w_syn_v`
  - `HIST` (`8,024`), `DA` (`396`), `OCT` (`101`), `SER` (`48`), and `UNKNOWN` (`47,206`) carry weight `0.0` (unassigned signs are never defaulted to excitatory).

## 2. Typed Intervention Distinctions (`AGENTS.md` §7.1, §10)

| Condition | Implementation | Physical / Circuit Interpretation |
|---|---|---|
| `acute_edge_mask` | `EdgeMaskModulation(pre=26 GABA, post=6 ascending relays, factor=0.0)` | Acute loss of direct `GABA -> ascending` inhibition (`26` interneurons remain intact in local VNC recurrent loops). |
| `gaba_atten_50pct` | `EdgeGainModulation(target=26 GABA, scope="outgoing", factor=0.5)` | Partial `-50%` functional loss of GABAergic synaptic efficacy across VNC targets. |
| `gaba_cell_death` | `NeuronSilencing(target=26 GABA, mode="both_zero")` | Complete functional loss proxy of the `26` GABAergic interneurons (zeroes both incoming excitation/inhibition and all outgoing inhibition, perturbing intra-VNC disinhibition). |
| `matched_ctrl_ablation` | `NeuronSilencing(target=26 matched VNC GABA, mode="both_zero")` | Structural specificity control matching degrees/synapse sums (`|SMD| <= 0.0970`) with `0` direct edges to ascending readouts. |

## 3. Windowed Readouts & Known Limitations

- **Trial Timeline (`0.8 s` total):** `pre_window = [0.0, 0.1) s` (spontaneous baseline), `stim_window = [0.1, 0.6) s` (stochastic Poisson tactile drive onto `30` `R-MesoLN` afferents, `weight_v = 0.06875 V`), `post_window = [0.6, 0.8] s` (post-stimulus persistence).
- **L1 Resting Silence:** Zero spontaneous background current keeps unstimulated `pre_window` and `sham_zero_stimulus` at `0.000 Hz`; persistence after `[0.1, 0.6) s` stimulus offsets is therefore limited by short synaptic/membrane time constants (`5–20 ms`) rather than persistent NMDA/metabotropic currents.
- **Computational Scope Only:** Does not include gap junctions (`shakB`), chronic caspase remodeling, glia (`11,864` annotated glia bodies), or descending pain modulation via monoamines/peptides.
