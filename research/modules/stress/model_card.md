# Model Card: `stress_allostatic_reactive_scope_v1` (L3, RUO)

- **Model ID / Revision:** `stress_allostatic_reactive_scope_v1` / `1.0`
- **Model Level & Solver:** `L3` continuous-time ODE (`scipy.integrate.solve_ivp`, `RK45`, `dt_eval_h = 0.05 h` = `180 s`, `duration_h = 48.0 h`)
- **Parameter Manifest SHA-256:** `252516ca0923eb9d682e6a229ffc9361b9a77fe5625ac030c74f874b7864905f`
- **Implementation:** [`packages/synapse_core/stress.py`](../../../packages/synapse_core/stress.py)
- **Intended Scope:** **Research Use Only (RUO)** macro-level reactive-scope defensive arousal and allostatic wear model coupled to L1 `malecns_v1_0` (`synapse_lif_v1`) defensive circuitry (`DNp01`, `DNp09`).
- **Safety Gate:** `diagnostic_label_guard_enabled = True` (validator enforces non-clinical scope — forbids human psychiatric diagnoses such as anxiety or depression).

## Quantitative Equations

1. **Defensive Arousal ($A \in [0, 1]$):** $\frac{dA}{dt} = k_{\mathrm{drive}} u(t)(1 - A) - \frac{1 + k_{\mathrm{fb}} C}{\tau_A} A$.
2. **Homeostatic Inhibitory Reserve ($C \in [c_{\min}, 1]$):** $\frac{dC}{dt} = \frac{1 - C}{\tau_C} - k_{\mathrm{wear}} \max(0, A - a_{\mathrm{thresh}})(C - c_{\min})$.
3. **Cumulative Allostatic Wear ($L \ge 0$):** $\frac{dL}{dt} = k_{\mathrm{load}} \max(0, A - a_{\mathrm{thresh}})\bigl(1 + \mathrm{load\_wear\_amp}(1 - C)\bigr) - \frac{L}{\tau_L}$.

## Verification Gates (`synapse stress verify`)

- `rk45_convergence_and_bounds`: `max_step = 0.05 h` vs `0.01 h` (`max_abs_diff = 1.184e-05 < 1e-4`), physical state bounds preserved.
- `sham_baseline_invariance`: exact equilibrium $(A=0, C=1, L=0)$ under $u(t)=0$.
- `acute_stress_habituation_and_recovery`: single 30-min bout yields `a_peak = 0.402`, preserves reserve (`c_min = 0.969 > 0.80`), returns to `0`.
- `chronic_allostatic_overload_separation`: 18 bouts over 36 h erode reserve (`c_min = 0.497 < 0.65`), amplify peak load `80.21x` vs. acute, and sensitize late-bout arousal (`0.524 > 0.430`).
- `post_chronic_washout_and_ruo_guard`: 27 h washout restores `C` from `0.545` to `0.934` and cuts load from `0.978` to `0.318`.

## Explicit Limitations

- L3 macro states summarize hours-scale plasticity/habituation phenomenologically; they do not explicitly integrate peptidergic release kinetics (`DH44`, `Crz`, `DILPs`).
- L1 coupling maps reserve loss cleanly onto synaptic gain multipliers on verified `GABA`/`GLUT` inputs rather than solving a 48 h stochastic LIF trajectory.
