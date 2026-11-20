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
from synapse_core.models import (
    ConstantCurrentStimulus,
    EdgeGainModulation,
    InterventionSpec,
    LIFParameters,
    NeuronSilencing,
    PoissonRateStimulus,
    ResolvedInterventionRecord,
    ShamIntervention,
    validate_model_spec,
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
    "DEFAULT_SIGN_MAP",
    "SEED_ALGORITHM",
    "BackendCapabilities",
    "Brian2CPUBackend",
    "ConstantCurrentStimulus",
    "DirectedConnectomeGraph",
    "DirectedEdge",
    "EdgeGainModulation",
    "InterventionSpec",
    "LIFParameters",
    "NeuronNamespaceKey",
    "NeuronSilencing",
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
    "UnsupportedBackendOptionError",
    "derive_seed",
    "extract_bounded_subgraph",
    "validate_model_spec",
]
