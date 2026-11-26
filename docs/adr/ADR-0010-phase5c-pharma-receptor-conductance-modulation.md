# ADR-0010: Phase 5C-2 Pharma L2 Dose-Independent Receptor Kinetics & L1 MaleCNS Coupling

> Status: Accepted (Exploratory RUO Baseline)  
> Date: 2026-11-26  
> Scope: `synapse_core.pharmacology`, `synapse_cli`, `research/modules/pharma/`, `P5-PHARMA-001-PILOT`

## Context

`AGENTS.md` §10 requires the Pharmacology (`Pharma`) module to begin strictly as a **dose-independent mechanistic** model (`named_compound_gate_enabled = False`): dimensionless receptor modulation without named pharmaceutical products, human dosing units, or clinical efficacy extrapolation. A circuit-level test bed also requires separating bidirectional GABA\_A (`Rdl`) conductance modulation (noncompetitive pore block vs. positive allosteric modulation), excitatory cholinergic (`nAChR`) attenuation, dual-target Bliss independence combinations, and anatomically matched off-pathway GABA controls.

## Decision

1. **Pure L2 Kernel (`packages/synapse_core/pharmacology.py`):**
   - Implement frozen Pydantic specification `ReceptorModulationParameters` (`model_id="receptor_conductance_modulation_v1"`, `model_level="L2"`, `solver="analytic_hill_schild"`, `dt_s=0.0`, `named_compound_gate_enabled=False`).
   - Parameterize concentration-response using strictly dimensionless normalized affinity ratios (`[A]/EC50`, `[B]/Ki`, `[I]/IC50`, `[M]/Km`) across a 46-point log-space grid `[10^-3, 10^3]`:
     - **Hill occupancy:** $E = x^n / (1 + x^n)$ (`rdl_gaba_a_hill_n = 1.6`, `nachr_ach_hill_n = 1.3`).
     - **Competitive Gaddum-Schild antagonism:** $E = x^n / (x^n + (1 + [\mathrm{B}]/K_i)^n)$ yielding unit Schild regression slope (`1.000000`) by root-solving apparent $\mathrm{EC}_{50}$.
     - **Noncompetitive pore block:** $\alpha = \mathrm{floor} + (1 - \mathrm{floor}) / (1 + ([\mathrm{I}]/\mathrm{IC}_{50})^n)$ for bidirectional `Rdl` disinhibition and `nAChR` attenuation.
     - **Positive allosteric modulation (PAM):** $\gamma = 1 + (\gamma_{\max} - 1) m^{h_m} / (1 + m^{h_m})$ (`rdl_pam_max_gain = 2.0`, `rdl_pam_hill_m = 1.2`, exact snapshot scale `1.75x` at `[M]/Km = 3^(1/1.2) ≈ 2.4980`).
     - **Bliss independence null:** $E_{\mathrm{Bliss}} = f_A + f_B - f_A f_B$ for independent-site dual-target suppression.
   - Enforce five quantitative verification gates via `verify_pharmacology_gates`.

2. **Isolated MaleCNS v1.0 L1 Coupling (`P5-PHARMA-001-PILOT`):**
   - Couple L2 snapshots explicitly to `malecns_v1_0` (`synapse_lif_v1`, `30` `ACH` `sensory_nachr_ach_targets` @ `40 Hz`, `26` `GABA` `rdl_gaba_feedforward_targets`, `26` `matched_vnc_gaba_controls`, primary ascending readouts `523539`, `558778`, `10592`) using declarative `edge_gain_modulation` and `edge_mask` interventions.
   - Separate specimen provenance strictly from `flywire_fafb_v630` and keep `P5-PHARMA-001.yaml` unfrozen (`status: draft`) until pilot calibration completes and a human freezes it.

## Consequences

- Zero modification to the L1 Brian2 LIF kernel, schemas, or strict DAG import boundaries (`synapse_core` imports only scientific stdlib/numpy/pydantic).
- Named compounds, mammalian/human pharmacokinetics, and receptor expression weighting beyond existing connectome NT assignments remain explicitly deferred behind `named_compound_gate_enabled = False`.
