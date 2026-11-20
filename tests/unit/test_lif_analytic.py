"""Analytical and numerical verification tests for Brian2CPUBackend LIF equations."""

from __future__ import annotations

import math

import numpy as np
import pytest

from synapse_core import (
    SEED_ALGORITHM,
    Brian2CPUBackend,
    ConstantCurrentStimulus,
    DirectedConnectomeGraph,
    DirectedEdge,
    LIFParameters,
    ResourceLimitError,
    SeedRecord,
    SimulationRequest,
)


def _single_neuron_graph() -> DirectedConnectomeGraph:
    return DirectedConnectomeGraph.from_edges(
        dataset_id="analytic_test",
        release="1.0",
        specimen_id="single_cell",
        is_synthetic_fixture=True,
        neuron_ids=("N0",),
        edges=[],
        neurotransmitters={"N0": "ACH"},
    )


def _seed_rec() -> SeedRecord:
    return SeedRecord(algorithm=SEED_ALGORITHM, master_seed=1, derived_seeds={"brian2": 12345})


@pytest.mark.unit
def test_zero_input_no_stimulus_control() -> None:
    backend = Brian2CPUBackend()
    params = LIFParameters(dt_s=0.0001)
    req = SimulationRequest(
        graph=_single_neuron_graph(),
        parameters=params,
        duration_s=0.1,
        seed_record=_seed_rec(),
        interventions=(),
        record_voltage_neuron_ids=("N0",),
    )
    res = backend.run(req)
    assert len(res.spike_times_s) == 0
    assert res.firing_rates_hz[0] == 0.0
    assert res.voltage_traces_v is not None
    np.testing.assert_allclose(res.voltage_traces_v["N0"], params.v_rest_v, atol=1e-12)


@pytest.mark.unit
def test_analytical_subthreshold_charging_and_passive_decay() -> None:
    backend = Brian2CPUBackend()
    params = LIFParameters(dt_s=0.0001)
    i_amp = 4e-10  # R_m * I = 10 MOhm * 0.4 nA = +4.0 mV (subthreshold vs +7.0 mV threshold)
    t_off = 0.04
    req = SimulationRequest(
        graph=_single_neuron_graph(),
        parameters=params,
        duration_s=0.10,
        seed_record=_seed_rec(),
        interventions=(
            ConstantCurrentStimulus(
                target_neuron_ids=("N0",), current_a=i_amp, start_s=0.0, end_s=t_off
            ),
        ),
        record_voltage_neuron_ids=("N0",),
    )
    res = backend.run(req)
    assert len(res.spike_times_s) == 0
    assert res.voltage_times_s is not None and res.voltage_traces_v is not None
    t = res.voltage_times_s
    v = res.voltage_traces_v["N0"]

    v_inf = params.v_rest_v + params.r_m_ohm * i_amp
    v_at_off = params.v_rest_v + (v_inf - params.v_rest_v) * (1.0 - np.exp(-t_off / params.tau_m_s))
    v_analytic = np.where(
        t <= t_off + 1e-12,
        params.v_rest_v + (v_inf - params.v_rest_v) * (1.0 - np.exp(-t / params.tau_m_s)),
        params.v_rest_v + (v_at_off - params.v_rest_v) * np.exp(-(t - t_off) / params.tau_m_s),
    )
    np.testing.assert_allclose(v, v_analytic, atol=1e-5)


@pytest.mark.unit
def test_analytical_suprathreshold_isi_and_dt_convergence() -> None:
    backend = Brian2CPUBackend()
    i_amp = 1.0e-9  # R_m * I = +10 mV -> v_inf = -42 mV > -45 mV threshold
    base_params = LIFParameters(dt_s=0.0001)
    v_inf = base_params.v_rest_v + base_params.r_m_ohm * i_amp
    isi_exact = base_params.t_ref_s + base_params.tau_m_s * math.log(
        (v_inf - base_params.v_reset_v) / (v_inf - base_params.v_threshold_v)
    )

    errors: list[float] = []
    for dt_s in (0.0002, 0.00005):
        params = LIFParameters(dt_s=dt_s)
        req = SimulationRequest(
            graph=_single_neuron_graph(),
            parameters=params,
            duration_s=0.5,
            seed_record=_seed_rec(),
            interventions=(ConstantCurrentStimulus(target_neuron_ids=("N0",), current_a=i_amp),),
        )
        res = backend.run(req)
        assert len(res.spike_times_s) >= 10
        mean_isi = float(np.mean(np.diff(res.spike_times_s)))
        errors.append(abs(mean_isi - isi_exact))

    # Finer dt must be strictly within 1 step and smaller error than coarse dt
    assert errors[1] < 0.0001
    assert errors[1] <= errors[0]


@pytest.mark.unit
def test_two_cell_excitatory_inhibitory_sign_and_synaptic_delay() -> None:
    backend = Brian2CPUBackend()
    params = LIFParameters(dt_s=0.0001, delay_s=0.005, w_syn_v=0.000275)

    g_exc = DirectedConnectomeGraph.from_edges(
        dataset_id="two_cell",
        release="1.0",
        specimen_id="two_cell",
        is_synthetic_fixture=True,
        neuron_ids=("PRE", "POST"),
        edges=[DirectedEdge("PRE", "POST", 20)],
        neurotransmitters={"PRE": "ACH", "POST": "ACH"},
    )
    g_inh = DirectedConnectomeGraph.from_edges(
        dataset_id="two_cell",
        release="1.0",
        specimen_id="two_cell",
        is_synthetic_fixture=True,
        neuron_ids=("PRE", "POST"),
        edges=[DirectedEdge("PRE", "POST", 20)],
        neurotransmitters={"PRE": "GABA", "POST": "ACH"},
    )

    # Strong brief pulse forces PRE to spike quickly around t ~ 1.5 ms
    stim = ConstantCurrentStimulus(
        target_neuron_ids=("PRE",), current_a=5.0e-9, start_s=0.0, end_s=0.005
    )
    res_exc = backend.run(
        SimulationRequest(
            graph=g_exc,
            parameters=params,
            duration_s=0.03,
            seed_record=_seed_rec(),
            interventions=(stim,),
            record_voltage_neuron_ids=("POST",),
        )
    )
    res_inh = backend.run(
        SimulationRequest(
            graph=g_inh,
            parameters=params,
            duration_s=0.03,
            seed_record=_seed_rec(),
            interventions=(stim,),
            record_voltage_neuron_ids=("POST",),
        )
    )

    pre_spikes = [
        t
        for nid, t in zip(res_exc.spike_neuron_ids, res_exc.spike_times_s, strict=True)
        if nid == "PRE"
    ]
    assert len(pre_spikes) >= 1
    first_pre = pre_spikes[0]

    assert res_exc.voltage_times_s is not None and res_exc.voltage_traces_v is not None
    assert res_inh.voltage_traces_v is not None
    t = res_exc.voltage_times_s
    v_post_exc = res_exc.voltage_traces_v["POST"]
    v_post_inh = res_inh.voltage_traces_v["POST"]

    # Before first_pre + delay_s, POST must remain strictly at rest
    pre_delay_mask = t < (first_pre + params.delay_s - 0.0002)
    np.testing.assert_allclose(v_post_exc[pre_delay_mask], params.v_rest_v, atol=1e-12)
    np.testing.assert_allclose(v_post_inh[pre_delay_mask], params.v_rest_v, atol=1e-12)

    # After delay, ACH depolarizes (> v_rest) and GABA hyperpolarizes (< v_rest)
    post_delay_mask = t > (first_pre + params.delay_s + 0.002)
    assert np.max(v_post_exc[post_delay_mask]) > params.v_rest_v + 1e-4
    assert np.min(v_post_inh[post_delay_mask]) < params.v_rest_v - 1e-4


@pytest.mark.unit
def test_resource_limit_enforced_without_silent_downsampling() -> None:
    backend = Brian2CPUBackend()
    req = SimulationRequest(
        graph=_single_neuron_graph(),
        parameters=LIFParameters(dt_s=0.0001),
        duration_s=0.1,
        seed_record=_seed_rec(),
        max_estimated_memory_bytes=128,
    )
    with pytest.raises(ResourceLimitError, match="exceeds cap"):
        backend.run(req)
