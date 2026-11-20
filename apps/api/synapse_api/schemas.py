"""Pydantic v2 request and response schemas for SYNAPSE HTTP API v1."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class ModelValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec: dict[str, Any]


class ProtocolValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_path: str | None = None
    yaml_text: str | None = None
    allow_unresolved: bool = False


class ProtocolFreezeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_path: str
    out_filename: str | None = None
    confirmed: bool = False


class ExperimentPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_path: str
    dataset_id: str
    replicates: int | None = Field(default=None, ge=1, le=500)


class SubgraphQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_neuron_ids: list[str] = Field(min_length=1, max_length=100)
    hops: int = Field(default=1, ge=0, le=4)
    direction: Literal["outgoing", "incoming", "both"] = "outgoing"
    min_synapses: int = Field(default=1, ge=1)
    max_nodes: int = Field(default=250, ge=1, le=5000)


class JobSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["protocol_experiment", "analysis", "export_bundle"]
    idempotency_key: str | None = Field(default=None, max_length=128)
    # protocol_experiment fields
    protocol_path: str | None = None
    dataset_id: str | None = None
    work_dir_name: str | None = None
    replicates: int | None = Field(default=None, ge=1, le=500)
    workers: int = Field(default=1, ge=1, le=8)
    # analysis fields
    runs_rel_dir: str | None = None
    out_rel_dir: str | None = None
    baseline_condition: str | None = None
    treatment_condition: str | None = None
    target_neuron_id: str | None = None
    # export_bundle fields
    analysis_rel_dir: str | None = None
