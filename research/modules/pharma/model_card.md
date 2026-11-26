# Model Card: `receptor_conductance_modulation_v1` (L2, RUO)

- **Model ID / Revision:** `receptor_conductance_modulation_v1` / `1.0`
- **Model Level & Solver:** `L2` analytic mechanistic kinetics (`analytic_hill_schild`, `dt_s = 0.0`)
- **Parameter Manifest SHA-256:** `94d070a7be603d220b14271a2106c6df9623aa0773a5b19b8fe7b501f9059ff7`
- **Implementation:** [`packages/synapse_core/pharmacology.py`](../../../packages/synapse_core/pharmacology.py)
- **Intended Scope:** **Research Use Only (RUO)** dose-independent receptor-occupancy and conductance-scaling calculator coupled to `synapse_lif_v1` (`malecns_v1_0`) via explicit edge-gain multipliers and edge masks.
- **Safety Gate:** `named_compound_gate_enabled = False` (enforced in Pydantic validator — forbids clinical dosing or named-drug extrapolation until external species-specific kinetic evidence gates are supplied).

## Quantitative Equations

1. **Hill Fractional Occupancy:** $E(x) = \frac{x^n}{1 + x^n}$, $x = [\mathrm{A}]/\mathrm{EC}_{50} \ge 0$.
2. **Competitive Gaddum–Schild Antagonism:** $E(x, b) = \frac{x^n}{x^n + (1 + b)^n}$, $b = [\mathrm{B}]/K_i \ge 0$.
3. **Noncompetitive Antagonist Conductance Scaling:** $\alpha(i) = \mathrm{floor} + (1 - \mathrm{floor}) \frac{1}{1 + i^n}$, $i = [\mathrm{I}]/\mathrm{IC}_{50} \ge 0$ (`rdl_gaba_a_hill_n = 1.6`, `nachr_ach_hill_n = 1.3`, `floor = 0.0`).
4. **Positive Allosteric Modulator (PAM) Gain:** $\gamma(m) = 1 + (\gamma_{\max} - 1)\frac{m^{h_m}}{1 + m^{h_m}}$, $m = [\mathrm{M}]/K_m \ge 0$ (`rdl_pam_max_gain = 2.0`, `rdl_pam_hill_m = 1.2`).
5. **Bliss Independence Expected Suppression:** $E_{\mathrm{Bliss}}(f_A, f_B) = f_A + f_B - f_A f_B \in [0, 1]$.

## Verification Gates (`synapse pharma verify`)

- `hill_boundary_and_half_max`: $E(0)=0$, $E(1)=0.5$, $E(10^6)>0.999999$ across `n in {1.0, 1.3, 1.6}`.
- `schild_linearity_and_slope`: Numerically root-solved Schild slope $= 1.0 \pm 10^{-6}$ (`R^2 > 0.999999`).
- `noncompetitive_vs_pam_directionality`: Strict monotonic decrease (`1.0 -> 0.0`) vs. monotonic increase (`1.0 -> 2.0`), exact half-maximal values (`0.5` at `IC50`, `1.5` at `Km`).
- `bliss_independence_identity`: Exact algebraic symmetry, zero-identity, and `(0.5, 0.5) -> 0.75`, `(0.3, 0.4) -> 0.58`.
- `ruo_dose_independent_guard`: Confirms dimensionless ratios and `named_compound_gate_enabled == False`.

## Explicit Limitations

- Does not model PK/PD absorption/metabolism, receptor desensitization kinetics, chloride reversal potential shifts, or metabotropic `GABA_B` / mAChR cascades.
- Direct synapse weighting assumes uniform receptor scaling across all outgoing predicted `GABA` or `ACH` edges of targeted cells.
