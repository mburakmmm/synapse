"""SYNAPSE core scientific kernel: graph types, LIF models, RNG, and backend interfaces."""

from synapse_core.backend import (
    BackendCapabilities,
    ResourceEstimate,
    ResourceLimitError,
    SimulationRequest,
    SimulationResult,
    SimulatorBackend,
    UnsupportedBackendOptionError,
)
from synapse_core.brian2_backend import Brian2CPUBackend
from synapse_core.circadian import (
    DEFAULT_Y0 as CIRCADIAN_DEFAULT_Y0,
)
from synapse_core.circadian import (
    CircadianHomeostaticParameters,
    TwoProcessTrajectory,
    detect_oscillation_peaks,
    run_shift_work_experiment,
    simulate_two_process,
    verify_circadian_homeostatic_gates,
    wrap_phase_hours,
)
from synapse_core.models import (
    ConstantCurrentStimulus,
    EdgeGainModulation,
    EdgeMaskModulation,
    InterventionSpec,
    LIFParameters,
    NeuronSilencing,
    PoissonRateStimulus,
    ResolvedInterventionRecord,
    ShamIntervention,
    validate_model_spec,
)
from synapse_core.plasticity import (
    MBPlasticityParameters,
    PlasticityTrajectory,
    compute_preference_metrics,
    run_conditioning_paradigm,
    simulate_conditioning_schedule,
    verify_plasticity_paradigm_gates,
)
from synapse_core.rng import SEED_ALGORITHM, SeedRecord, derive_seed
from synapse_core.subgraph import (
    SubgraphBoundExceededError,
    SubgraphMetadata,
    extract_bounded_subgraph,
)
from synapse_core.types import (
    DEFAULT_SIGN_MAP,
    DirectedConnectomeGraph,
    DirectedEdge,
    NeuronNamespaceKey,
)

__all__ = [
    "CIRCADIAN_DEFAULT_Y0",
    "DEFAULT_SIGN_MAP",
    "SEED_ALGORITHM",
    "BackendCapabilities",
    "Brian2CPUBackend",
    "CircadianHomeostaticParameters",
    "ConstantCurrentStimulus",
    "DirectedConnectomeGraph",
    "DirectedEdge",
    "EdgeGainModulation",
    "EdgeMaskModulation",
    "InterventionSpec",
    "LIFParameters",
    "MBPlasticityParameters",
    "NeuronNamespaceKey",
    "NeuronSilencing",
    "PlasticityTrajectory",
    "PoissonRateStimulus",
    "ResolvedInterventionRecord",
    "ResourceEstimate",
    "ResourceLimitError",
    "SeedRecord",
    "ShamIntervention",
    "SimulationRequest",
    "SimulationResult",
    "SimulatorBackend",
    "SubgraphBoundExceededError",
    "SubgraphMetadata",
    "TwoProcessTrajectory",
    "UnsupportedBackendOptionError",
    "compute_preference_metrics",
    "derive_seed",
    "detect_oscillation_peaks",
    "extract_bounded_subgraph",
    "run_conditioning_paradigm",
    "run_shift_work_experiment",
    "simulate_conditioning_schedule",
    "simulate_two_process",
    "validate_model_spec",
    "verify_circadian_homeostatic_gates",
    "verify_plasticity_paradigm_gates",
    "wrap_phase_hours",
]
