# Model Card: `shiu2024_lif` (v1.0)

> **RESEARCH USE ONLY (RUO):** Reduced whole-brain Leaky Integrate-and-Fire (LIF) dynamical model for adult *Drosophila melanogaster* connectome simulation. Not validated for human physiology, clinical decision-making, or drug efficacy.

## Identification & Provenance

- **Model ID:** `shiu2024_lif` (`revision: 1.0`)
- **Parameter Manifest SHA-256:** `12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`
- **Implementation:** [`LIFParameters.shiu2024_reference`](../../packages/synapse_core/models.py), [`Brian2CPUBackend`](../../packages/synapse_core/brian2_backend.py) (`_LIF_EQUATIONS_SHIU`)
- **Primary Reference:** Shiu, P. K. et al., *A Drosophila computational brain model reveals sensorimotor processing*, **Nature** (2024), DOI `10.1038/s41586-024-07763-9`
- **Reference Code Commit:** `philshiu/Drosophila_brain_model@91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`

## Mathematical Specification

All units are strictly SI inside SYNAPSE (`volt`, `second`, `amp`, `ohm`):

```text
dv/dt = (v_rest - v + g + r_m * I_ext) / tau_m : volt (unless refractory)
dg/dt = -g / tau_syn                           : volt (unless refractory)
Threshold: v > v_threshold
Reset:     v = v_reset; g = 0 * volt
Refractory period: rfc (= t_ref_s by default; 0 s if PoissonRateStimulus.disable_refractory=True)
Synaptic event (pre -> post, delay = delay_s): on_pre = "g += w"
External Poisson drive: PoissonInput(target_var="v", N=1, rate=rate_hz/second, weight=weight_v*volt)
```

In `brian2 2.10.1`, `(unless refractory)` on `dg/dt` causes `synapses_pre` to gate postsynaptic `on_pre` updates by `not_refractory`, so incoming synaptic events arriving while the postsynaptic neuron is refractory are ignored (matching upstream `model.py`).

### Frozen Parameters (`parameter_manifest_sha256=12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`)

| Symbol | Value | Units | Source / Role |
|---|---:|---|---|
| `v_rest_v` | `-0.052` | V | Resting potential (`-52 mV`) |
| `v_reset_v` | `-0.052` | V | Reset potential (`-52 mV`) |
| `v_threshold_v` | `-0.045` | V | Spike threshold (`-45 mV`) |
| `tau_m_s` | `0.020` | s | Membrane time constant (`20 ms`) |
| `tau_syn_s` | `0.005` | s | Synaptic decay constant (`5 ms`) |
| `t_ref_s` | `0.0022` | s | Absolute refractory period (`2.2 ms`) |
| `delay_s` | `0.0018` | s | Uniform axonal/synaptic delay (`1.8 ms`) |
| `w_syn_v` | `0.000275` | V | Scalar postsynaptic depolarization per synapse (`0.275 mV`) |
| `r_m_ohm` | `10000000.0` | Ω | Uniform membrane resistance (`10 MΩ`) |
| `dt_s` | `0.0001` | s | Integration timestep (`0.1 ms`) |
| `solver` | `"linear"` | — | Brian2 linear ODE integrator (`numpy` codegen target) |
| `dg_unless_refractory` | `true` | bool | Matches upstream `dg/dt` `(unless refractory)` qualifier |
| `unknown_nt_policy` | `"zero_effect"` | — | Neurons without resolvable excitatory/inhibitory sign contribute `0` weight |

## Intended Scope and Key Scientific Limitations

1. **Synapse Count ≠ Conductance:** Synaptic weights scale strictly as `edge_synapse_count * sign * w_syn_v` (`0.275 mV`); receptor kinetics, short-term plasticity, gap junctions, neuromodulators, and dendritic filtering are absent.
2. **Sign-Only Transmitter Mapping on `flywire_fafb_v630`:** Upstream `flywire_fafb_v630` carries signed phenotypes (`EXCITATORY_SIGN`, `INHIBITORY_SIGN`, `UNKNOWN`), not receptor-resolved post-synaptic responses.
3. **Homogeneous Single-Compartment Neurons:** Passive properties (`tau_m`, `v_threshold`, `v_reset`, `t_ref`) do not vary by cell class.
4. **Reproduction ≠ Biological Validation:** Agreement with `philshiu/Drosophila_brain_model@91bdd1e` demonstrates **computational reproduction** under the specified equations; it does not constitute independent wet-lab biological validation or clinical relevance.
