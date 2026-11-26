# ADR-0011: Phase 5C-3 Stress L3 Reactive-Scope Allostatic ODEs & L1 Defensive Circuitry

> Status: Accepted (Exploratory RUO Baseline)  
> Date: 2026-11-26  
> Scope: `synapse_core.stress`, `synapse_cli`, `research/modules/stress/`, `P5-STRESS-001-PILOT`

## Context

`AGENTS.md` §1 and §10 permit modeling declared fly-level defensive arousal and stress-related circuitry (`Stress`) only while strictly banning human clinical psychiatric labels (`anxiety`, `depression` diagnosis). Adult *Drosophila* expose two anatomically mapped defensive descending outputs (`DNp01` Giant Fiber escape driven strongly by `LC4`; `DNp09` freezing driven via visual threat pathways including `LC9`) regulated by dense `GABA`/`GLUT` inhibition, alongside slow hours-scale reactive-scope adaptation vs. allostatic load under repetitive threats.

## Decision

1. **L3 Reactive-Scope Allostatic ODEs (`packages/synapse_core/stress.py`):**
   - Frozen `StressAllostaticParameters` (`model_id="stress_allostatic_reactive_scope_v1"`, `model_level="L3"`, `solver="RK45"`, `dt_eval_h=0.05 h`, `duration_h=48.0 h`, `diagnostic_label_guard_enabled=True`).
   - Three coupled macro-states on an hours timescale using $C^1$ smooth pulses (`ramp_h = 0.15 h`): defensive arousal $A \in [0, 1]$, inhibitory reactive-scope reserve $C \in [c_{\min}, 1]$, and cumulative allostatic wear $L \ge 0$.
   - Verify 5 analytical/numerical gates via `verify_stress_allostatic_gates`: RK45 convergence & bounds, sham baseline invariance, acute habituation & recovery, chronic overload (`>= 3x` load and reserve-erosion arousal sensitization), and post-chronic washout recovery + RUO diagnostic guard.

2. **L1 MaleCNS v1.0 Defensive Circuit Mapping (`P5-STRESS-001-PILOT`):**
   - Map acute threat intensity (`30 Hz` vs `60 Hz` onto top `20` `LC4`->`DNp01` + top `20` `LC9`->`DNp09` `ACH` sensory neurons), L3 reserve erosion (`0.5x` outgoing gain or `0.0x` focal `edge_mask` on top `30` `GABA`/`GLUT` inputs to `DNp01/DNp09`), and sensory sensitization (`1.4x` threat gain + `0.5x` inhibitory gate).
   - Compare strictly against two Hungarian-matched negative control populations with zero direct synapses onto `DNp01/DNp09/DNp11` (`40` non-defensive `visual_projection` `ACH` neurons, `max|SMD| = 0.0676`; `30` off-pathway `GABA`/`GLUT` neurons, `max|SMD| = 0.1279`).

## Consequences

- Zero edits to Brian2 LIF kernel or schemas. Peptidergic endocrine compartments (`DH44`/`IPC`) are noted in the evidence register (`UNKNOWN` flat NT labels in MaleCNS) and explicitly excluded from L1 synaptic weight fabrication.
- Confirmatory protocol `P5-STRESS-001.yaml` remains an unfrozen draft (`status: draft`) pending human review and freeze.
