"""SYNAPSE experiment protocol validation, deterministic run orchestration, and benchmarks."""

from synapse_experiments.benchmark import BenchmarkError, evaluate_shiu2024_benchmark
from synapse_experiments.controls import select_matched_control_neurons
from synapse_experiments.job_control import (
    cancel_local_job,
    get_local_job_status,
    mark_incomplete_runs_cancelled,
    start_local_job,
)
from synapse_experiments.protocol import (
    ProtocolValidationError,
    freeze_protocol,
    load_and_validate_protocol,
    validate_run_manifest_schema,
)
from synapse_experiments.runner import (
    collect_source_provenance,
    execute_single_run,
    load_graph_from_dataset,
    plan_protocol_experiment,
    run_protocol_experiment,
)

__all__ = [
    "BenchmarkError",
    "ProtocolValidationError",
    "cancel_local_job",
    "collect_source_provenance",
    "evaluate_shiu2024_benchmark",
    "execute_single_run",
    "freeze_protocol",
    "get_local_job_status",
    "load_and_validate_protocol",
    "load_graph_from_dataset",
    "mark_incomplete_runs_cancelled",
    "plan_protocol_experiment",
    "run_protocol_experiment",
    "select_matched_control_neurons",
    "start_local_job",
    "validate_run_manifest_schema",
]
