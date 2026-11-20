"""Brian2 CPU reference backend for unit-consistent LIF network simulation."""

from __future__ import annotations

import itertools
import math
import time
from collections import defaultdict
from typing import Any

import numpy as np
from brian2 import (
    Clock,
    Network,
    NeuronGroup,
    PoissonInput,
    SpikeMonitor,
    StateMonitor,
    Synapses,
    amp,
    prefs,
    second,
    seed,
    volt,
)

from synapse_core.backend import (
    BackendCapabilities,
    ResourceEstimate,
    ResourceLimitError,
    SimulationRequest,
    SimulationResult,
    UnsupportedBackendOptionError,
)
from synapse_core.models import (
    ConstantCurrentStimulus,
    EdgeGainModulation,
    NeuronSilencing,
    PoissonRateStimulus,
    ResolvedInterventionRecord,
    ShamIntervention,
)
from synapse_core.types import DEFAULT_SIGN_MAP

_LIF_EQUATIONS = """
dv/dt = (v_rest - v + g + r_m * I_ext) / tau_m : volt (unless refractory)
dg/dt = -g / tau_syn : volt
I_ext : amp
rfc : second
"""

_LIF_EQUATIONS_SHIU = """
dv/dt = (v_rest - v + g + r_m * I_ext) / tau_m : volt (unless refractory)
dg/dt = -g / tau_syn : volt (unless refractory)
I_ext : amp
rfc : second
"""


class Brian2CPUBackend:
    """Deterministic CPU reference simulator backed by Brian2's pure-NumPy target."""

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id="brian2_cpu",
            device="cpu",
            precision="float64",
            supported_solvers=("exact", "linear", "euler"),
            supports_delays=True,
            supports_poisson_input=True,
            supports_constant_current=True,
            reproducibility_class="deterministic_seeded_cpu_single_process",
        )

    @staticmethod
    def estimate_from_counts(
        *,
        n_neurons: int,
        n_edges: int,
        duration_s: float,
        dt_s: float,
        n_voltage_monitored: int = 0,
    ) -> ResourceEstimate:
        n_timesteps = max(1, math.ceil(duration_s / dt_s))
        # Conservative estimate: neuron state + edge arrays + spike/state monitor buffers
        est_bytes = (
            4 * 1024 * 1024
            + n_neurons * 128
            + n_edges * 64
            + n_voltage_monitored * n_timesteps * 16
        )
        return ResourceEstimate(
            n_neurons=n_neurons,
            n_edges=n_edges,
            n_timesteps=n_timesteps,
            n_voltage_monitored=n_voltage_monitored,
            estimated_memory_bytes=est_bytes,
        )

    def estimate_resources(self, request: SimulationRequest) -> ResourceEstimate:
        if not math.isfinite(request.duration_s) or request.duration_s <= 0.0:
            raise ValueError(f"duration_s must be finite and > 0, got {request.duration_s}")
        m_end = (
            request.duration_s if request.measurement_end_s is None else request.measurement_end_s
        )
        if request.measurement_start_s < 0.0 or m_end <= request.measurement_start_s:
            raise ValueError("Invalid measurement window bounds")
        if m_end > request.duration_s:
            raise ValueError("measurement_end_s cannot exceed duration_s")

        return self.estimate_from_counts(
            n_neurons=request.graph.n_neurons,
            n_edges=request.graph.n_edges,
            duration_s=request.duration_s,
            dt_s=request.parameters.dt_s,
            n_voltage_monitored=len(request.record_voltage_neuron_ids),
        )

    def run(self, request: SimulationRequest) -> SimulationResult:
        caps = self.capabilities()
        params = request.parameters
        if params.solver not in caps.supported_solvers:
            raise UnsupportedBackendOptionError(
                f"Solver {params.solver!r} is not supported by {caps.backend_id}"
            )
        estimate = self.estimate_resources(request)
        if (
            request.max_estimated_memory_bytes is not None
            and estimate.estimated_memory_bytes > request.max_estimated_memory_bytes
        ):
            raise ResourceLimitError(
                f"Estimated memory {estimate.estimated_memory_bytes} bytes exceeds cap "
                f"{request.max_estimated_memory_bytes} bytes"
            )

        if "brian2" not in request.seed_record.derived_seeds:
            raise ValueError("SeedRecord must contain 'brian2' derived seed")
        brian2_seed = request.seed_record.derived_seeds["brian2"]

        graph = request.graph
        pre_idx, post_idx, counts = graph.edge_arrays()

        # Compute signed baseline weights from presynaptic neurotransmitters without mutating graph
        col_signs = np.zeros(graph.n_neurons, dtype=np.float64)
        for idx, nt in enumerate(graph.neurotransmitters):
            if nt is None or nt not in DEFAULT_SIGN_MAP:
                if params.unknown_nt_policy == "error":
                    raise ValueError(
                        f"Unknown neurotransmitter {nt!r} for neuron {graph.neuron_ids[idx]!r}"
                    )
                col_signs[idx] = 0.0
            else:
                col_signs[idx] = DEFAULT_SIGN_MAP[nt]
        edge_weights_v = counts.astype(np.float64) * col_signs[pre_idx] * params.w_syn_v

        resolved_records: list[ResolvedInterventionRecord] = []
        constant_stimuli: list[tuple[ConstantCurrentStimulus, tuple[int, ...]]] = []
        poisson_stimuli: list[tuple[PoissonRateStimulus, tuple[int, ...]]] = []

        for order_idx, intervention in enumerate(request.interventions):
            if isinstance(intervention, ShamIntervention):
                resolved_records.append(
                    ResolvedInterventionRecord(
                        order_index=order_idx,
                        kind=intervention.kind,
                        resolved_target_ids=(),
                        affected_edge_count=0,
                        parameter_delta={"description": intervention.description},
                        units="none",
                        start_s=0.0,
                        end_s=request.duration_s,
                    )
                )
                continue

            target_indices = tuple(graph.index_of(nid) for nid in intervention.target_neuron_ids)
            target_set = set(target_indices)

            if isinstance(intervention, EdgeGainModulation):
                mask = np.zeros(len(edge_weights_v), dtype=bool)
                if intervention.scope in ("outgoing", "both"):
                    mask |= np.isin(pre_idx, list(target_set))
                if intervention.scope in ("incoming", "both"):
                    mask |= np.isin(post_idx, list(target_set))
                edge_weights_v[mask] *= intervention.factor
                resolved_records.append(
                    ResolvedInterventionRecord(
                        order_index=order_idx,
                        kind=intervention.kind,
                        resolved_target_ids=intervention.target_neuron_ids,
                        affected_edge_count=int(np.count_nonzero(mask)),
                        parameter_delta={
                            "scope": intervention.scope,
                            "factor": intervention.factor,
                        },
                        units="dimensionless_multiplier",
                        start_s=0.0,
                        end_s=request.duration_s,
                    )
                )
            elif isinstance(intervention, NeuronSilencing):
                mask = np.zeros(len(edge_weights_v), dtype=bool)
                if intervention.mode in ("outgoing_zero", "both_zero"):
                    mask |= np.isin(pre_idx, list(target_set))
                if intervention.mode in ("incoming_zero", "both_zero"):
                    mask |= np.isin(post_idx, list(target_set))
                edge_weights_v[mask] = 0.0
                resolved_records.append(
                    ResolvedInterventionRecord(
                        order_index=order_idx,
                        kind=intervention.kind,
                        resolved_target_ids=intervention.target_neuron_ids,
                        affected_edge_count=int(np.count_nonzero(mask)),
                        parameter_delta={"mode": intervention.mode, "weight_v": 0.0},
                        units="V",
                        start_s=0.0,
                        end_s=request.duration_s,
                    )
                )
            elif isinstance(intervention, ConstantCurrentStimulus):
                constant_stimuli.append((intervention, target_indices))
                resolved_records.append(
                    ResolvedInterventionRecord(
                        order_index=order_idx,
                        kind=intervention.kind,
                        resolved_target_ids=intervention.target_neuron_ids,
                        affected_edge_count=0,
                        parameter_delta={"current_a": intervention.current_a},
                        units="A",
                        start_s=intervention.start_s,
                        end_s=intervention.end_s,
                    )
                )
            elif isinstance(intervention, PoissonRateStimulus):
                poisson_stimuli.append((intervention, target_indices))
                resolved_records.append(
                    ResolvedInterventionRecord(
                        order_index=order_idx,
                        kind=intervention.kind,
                        resolved_target_ids=intervention.target_neuron_ids,
                        affected_edge_count=0,
                        parameter_delta={
                            "rate_hz": intervention.rate_hz,
                            "weight_v": intervention.weight_v,
                            "disable_refractory": intervention.disable_refractory,
                        },
                        units="Hz,V",
                        start_s=intervention.start_s,
                        end_s=intervention.end_s,
                    )
                )
            else:
                raise UnsupportedBackendOptionError(
                    f"Unsupported intervention specification: {type(intervention).__name__}"
                )

        prev_target = prefs.codegen.target
        prefs.codegen.target = "numpy"
        t_wall_start = time.perf_counter()
        try:
            seed(brian2_seed)
            clock = Clock(dt=params.dt_s * second)
            namespace: dict[str, Any] = {
                "v_rest": params.v_rest_v * volt,
                "v_reset": params.v_reset_v * volt,
                "v_threshold": params.v_threshold_v * volt,
                "tau_m": params.tau_m_s * second,
                "tau_syn": params.tau_syn_s * second,
                "r_m": params.r_m_ohm * volt / amp,
            }
            eqs = _LIF_EQUATIONS_SHIU if params.dg_unless_refractory else _LIF_EQUATIONS
            neu = NeuronGroup(
                N=graph.n_neurons,
                model=eqs,
                method=params.solver,
                threshold="v > v_threshold",
                reset="v = v_reset; g = 0 * volt",
                refractory="rfc",
                name="synapse_neurons",
                namespace=namespace,
                dt=clock.dt,
            )
            neu.v = params.v_rest_v * volt
            neu.g = 0.0 * volt
            neu.I_ext = 0.0 * amp
            neu.rfc = params.t_ref_s * second

            net_objects: list[Any] = [neu]

            if len(edge_weights_v) > 0:
                syn = Synapses(
                    neu,
                    neu,
                    "w : volt",
                    on_pre="g += w",
                    delay=params.delay_s * second,
                    name="synapse_connections",
                    dt=clock.dt,
                )
                syn.connect(i=pre_idx, j=post_idx)
                syn.w = edge_weights_v * volt
                net_objects.append(syn)

            # Build Poisson inputs and track active schedules
            poisson_items: list[tuple[PoissonRateStimulus, Any]] = []
            for stim, target_indices in poisson_stimuli:
                for n_idx in target_indices:
                    if stim.disable_refractory:
                        neu[n_idx].rfc = 0.0 * second
                    p_inp = PoissonInput(
                        target=neu[n_idx : n_idx + 1],
                        target_var="v",
                        N=1,
                        rate=stim.rate_hz / second,
                        weight=stim.weight_v * volt,
                    )
                    poisson_items.append((stim, p_inp))
                    net_objects.append(p_inp)

            spk_mon = SpikeMonitor(neu, name="spike_monitor")
            net_objects.append(spk_mon)

            v_mon: StateMonitor | None = None
            record_indices = [graph.index_of(nid) for nid in request.record_voltage_neuron_ids]
            if record_indices:
                v_mon = StateMonitor(
                    neu,
                    "v",
                    record=record_indices,
                    name="voltage_monitor",
                    dt=clock.dt,
                )
                net_objects.append(v_mon)

            net = Network(*net_objects)

            # Split duration at stimulus start/end boundaries
            breakpoints = {0.0, request.duration_s}
            for stim_c, _ in constant_stimuli:
                if 0.0 < stim_c.start_s < request.duration_s:
                    breakpoints.add(stim_c.start_s)
                if stim_c.end_s is not None and 0.0 < stim_c.end_s < request.duration_s:
                    breakpoints.add(stim_c.end_s)
            for stim_p, _ in poisson_stimuli:
                if 0.0 < stim_p.start_s < request.duration_s:
                    breakpoints.add(stim_p.start_s)
                if stim_p.end_s is not None and 0.0 < stim_p.end_s < request.duration_s:
                    breakpoints.add(stim_p.end_s)

            sorted_pts = sorted(breakpoints)
            for t_a, t_b in itertools.pairwise(sorted_pts):
                seg_dur = t_b - t_a
                if seg_dur <= 1e-12:
                    continue
                t_mid = 0.5 * (t_a + t_b)

                # Update per-neuron constant current for this segment
                i_ext_vec = np.zeros(graph.n_neurons, dtype=np.float64)
                for stim_c, target_indices in constant_stimuli:
                    end_c = request.duration_s if stim_c.end_s is None else stim_c.end_s
                    if stim_c.start_s <= t_mid < end_c:
                        for idx in target_indices:
                            i_ext_vec[idx] += stim_c.current_a
                neu.I_ext = i_ext_vec * amp

                # Toggle Poisson input active flags for this segment
                for stim_p, p_inp in poisson_items:
                    end_p = request.duration_s if stim_p.end_s is None else stim_p.end_s
                    p_inp.active = bool(stim_p.start_s <= t_mid < end_p)

                net.run(seg_dur * second)
                if (
                    request.max_wall_seconds is not None
                    and (time.perf_counter() - t_wall_start) > request.max_wall_seconds
                ):
                    raise ResourceLimitError(
                        f"Simulation exceeded max_wall_seconds={request.max_wall_seconds}"
                    )

            wall_seconds = time.perf_counter() - t_wall_start
            if request.max_wall_seconds is not None and wall_seconds > request.max_wall_seconds:
                raise ResourceLimitError(
                    f"Simulation exceeded max_wall_seconds={request.max_wall_seconds}"
                )

            # Extract spikes within measurement window
            raw_i = np.asarray(spk_mon.i, dtype=np.int64)
            raw_t = np.asarray(spk_mon.t / second, dtype=np.float64)
            m_start = request.measurement_start_s
            m_end = (
                request.duration_s
                if request.measurement_end_s is None
                else request.measurement_end_s
            )
            m_dur = m_end - m_start
            win_mask = (raw_t >= m_start) & (raw_t <= m_end)
            filt_i = raw_i[win_mask]
            filt_t = raw_t[win_mask]

            # Deterministic sort by (time, neuron_index)
            if len(filt_t) > 0:
                order = np.lexsort((filt_i, filt_t))
                filt_i = filt_i[order]
                filt_t = filt_t[order]

            counts_per_neuron: dict[int, int] = defaultdict(int)
            for idx_val in filt_i.tolist():
                counts_per_neuron[idx_val] += 1
            rates_hz = np.array(
                [counts_per_neuron[i] / m_dur for i in range(graph.n_neurons)],
                dtype=np.float64,
            )

            spike_nids = tuple(graph.neuron_ids[int(idx)] for idx in filt_i)

            voltage_times_s: np.ndarray | None = None
            voltage_traces_v: dict[str, np.ndarray] | None = None
            if v_mon is not None:
                voltage_times_s = np.asarray(v_mon.t / second, dtype=np.float64)
                voltage_traces_v = {
                    nid: np.asarray(v_mon.v[pos] / volt, dtype=np.float64)
                    for pos, nid in enumerate(request.record_voltage_neuron_ids)
                }

            return SimulationResult(
                backend_id=caps.backend_id,
                precision=caps.precision,
                neuron_ids=graph.neuron_ids,
                spike_neuron_ids=spike_nids,
                spike_times_s=filt_t,
                firing_rates_hz=rates_hz,
                measurement_duration_s=m_dur,
                resolved_interventions=tuple(resolved_records),
                resource_estimate=estimate,
                wall_seconds=wall_seconds,
                voltage_times_s=voltage_times_s,
                voltage_traces_v=voltage_traces_v,
                warnings=(),
            )
        finally:
            prefs.codegen.target = prev_target
