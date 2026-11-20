"""Simulator backend protocol, resource estimation types, and explicit error classes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from synapse_core.models import InterventionSpec, LIFParameters, ResolvedInterventionRecord
from synapse_core.rng import SeedRecord
from synapse_core.types import DirectedConnectomeGraph


class ResourceLimitError(RuntimeError):
    """Raised when estimated simulation resources exceed protocol caps."""


class UnsupportedBackendOptionError(ValueError):
    """Raised when a requested solver or backend option is unsupported."""


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    """Explicit declaration of what a SimulatorBackend supports."""

    backend_id: str
    device: str
    precision: str
    supported_solvers: tuple[str, ...]
    supports_delays: bool
    supports_poisson_input: bool
    supports_constant_current: bool
    reproducibility_class: str


@dataclass(frozen=True, slots=True)
class ResourceEstimate:
    """Pre-dispatch resource footprint estimate."""

    n_neurons: int
    n_edges: int
    n_timesteps: int
    n_voltage_monitored: int
    estimated_memory_bytes: int


@dataclass(frozen=True, slots=True)
class SimulationRequest:
    """Complete immutable specification for a single simulation execution."""

    graph: DirectedConnectomeGraph
    parameters: LIFParameters
    duration_s: float
    seed_record: SeedRecord
    interventions: Sequence[InterventionSpec] = ()
    record_voltage_neuron_ids: Sequence[str] = ()
    max_wall_seconds: float | None = None
    max_estimated_memory_bytes: int | None = None
    measurement_start_s: float = 0.0
    measurement_end_s: float | None = None


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Standardized simulation output returned by all SimulatorBackend implementations."""

    backend_id: str
    precision: str
    neuron_ids: tuple[str, ...]
    spike_neuron_ids: tuple[str, ...]
    spike_times_s: np.ndarray
    firing_rates_hz: np.ndarray
    measurement_duration_s: float
    resolved_interventions: tuple[ResolvedInterventionRecord, ...]
    resource_estimate: ResourceEstimate
    wall_seconds: float
    voltage_times_s: np.ndarray | None = None
    voltage_traces_v: dict[str, np.ndarray] | None = None
    warnings: tuple[str, ...] = ()


class SimulatorBackend(Protocol):
    """Backend interface decoupled from orchestration, API, and database layers."""

    def capabilities(self) -> BackendCapabilities: ...

    def estimate_resources(self, request: SimulationRequest) -> ResourceEstimate: ...

    def run(self, request: SimulationRequest) -> SimulationResult: ...
