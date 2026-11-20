# Model Card: Metabolic L1 Presynaptic Gain Extension (`MET-001`)

- **Base Model:** `shiu2024_lif` (`revision: 1.0`, `parameter_manifest_sha256=12bc0160d0476aa4c65e8276d077e7e51afc45724e17eb667f6256763c9fa2e5`)
- **Intervention Mechanism:** `EdgeGainModulation(target_neuron_ids=..., scope="outgoing", factor in {1.25, 1.50})` applied atop `flywire_fafb_v630` signed synaptic weights (`w = counts * sign * 0.275 mV * factor`) without mutating the underlying sparse graph.
- **Endpoints:** Primary: `MN9_right` (`720575940660219265`) firing rate (Hz). Secondary: `MN9_left` (`720575940645521262`) firing rate (Hz). Negative control: `sham` (`0 Hz` expected total spikes = `0`). Structural specificity control: identical outgoing gain factor (`1.50`) applied to 21 structurally matched `EXCITATORY_SIGN` non-gustatory neurons excluding 1-hop downstream targets.

## Validation Boundary

- Phase 2 reproduction of unmodulated `100 Hz` sugar stimulation (`SHIU2024-FEEDING-BENCHMARK`) does **not** transfer biological validation to `EdgeGainModulation` hunger gain hypotheses.
- Outputs measure **modeled fly MN9 firing response shifts** conditional on the frozen FlyWire v630 graph and L1 equations — never human appetite, BMI, metabolic syndrome, or clinical efficacy.
