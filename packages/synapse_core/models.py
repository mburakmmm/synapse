"""SI unit-consistent LIF model parameters and typed immutable interventions."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class LIFParameters(BaseModel):
    """Explicitly parameterized leaky integrate-and-fire model in strict SI units."""

    model_config = ConfigDict(frozen=True)

    model_id: str = "synapse_lif_v1"
    model_revision: str = "1.0"
    v_rest_v: float = -0.052
    v_reset_v: float = -0.052
    v_threshold_v: float = -0.045
    tau_m_s: float = 0.020
    tau_syn_s: float = 0.005
    t_ref_s: float = 0.0022
    delay_s: float = 0.0018
    w_syn_v: float = 0.000275
    r_m_ohm: float = 10_000_000.0
    dt_s: float = 0.0001
    solver: Literal["exact", "linear", "euler"] = "exact"
    dg_unless_refractory: bool = False
    unknown_nt_policy: Literal["zero_effect", "error"] = "zero_effect"
    parameter_source: str = (
        "Reference Drosophila LIF defaults (Kakaria & de Bivort 2017; Jurgensen et al. 2021; "
        "Lazar et al. 2021; Paul et al. 2015; Shiu et al. 2024)"
    )

    @classmethod
    def shiu2024_reference(cls) -> LIFParameters:
        """Exact Shiu et al. (2024) LIF parameters matching philshiu/Drosophila_brain_model."""
        return cls(
            model_id="shiu2024_lif",
            model_revision="1.0",
            v_rest_v=-0.052,
            v_reset_v=-0.052,
            v_threshold_v=-0.045,
            tau_m_s=0.020,
            tau_syn_s=0.005,
            t_ref_s=0.0022,
            delay_s=0.0018,
            w_syn_v=0.000275,
            r_m_ohm=10_000_000.0,
            dt_s=0.0001,
            solver="linear",
            dg_unless_refractory=True,
            unknown_nt_policy="zero_effect",
            parameter_source=(
                "Shiu et al. Nature 2024 (10.1038/s41586-024-07763-9); "
                "philshiu/Drosophila_brain_model@91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"
            ),
        )

    @model_validator(mode="after")
    def _validate_physics(self) -> LIFParameters:
        numeric_fields = (
            "v_rest_v",
            "v_reset_v",
            "v_threshold_v",
            "tau_m_s",
            "tau_syn_s",
            "t_ref_s",
            "delay_s",
            "w_syn_v",
            "r_m_ohm",
            "dt_s",
        )
        for name in numeric_fields:
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        if self.tau_m_s <= 0.0 or self.tau_syn_s <= 0.0:
            raise ValueError("tau_m_s and tau_syn_s must be strictly positive")
        if self.t_ref_s < 0.0 or self.delay_s < 0.0 or self.w_syn_v < 0.0:
            raise ValueError("t_ref_s, delay_s, and w_syn_v must be non-negative")
        if self.r_m_ohm <= 0.0 or self.dt_s <= 0.0:
            raise ValueError("r_m_ohm and dt_s must be strictly positive")
        if self.v_threshold_v <= self.v_reset_v:
            raise ValueError("v_threshold_v must exceed v_reset_v")
        return self

    def canonical_sha256(self) -> str:
        """Compute canonical SHA-256 digest of the model parameter manifest."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConstantCurrentStimulus(BaseModel):
    """Time-bounded external current injection (amperes) to target neurons."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["constant_current"] = "constant_current"
    target_neuron_ids: tuple[str, ...] = Field(min_length=1)
    current_a: float
    start_s: float = 0.0
    end_s: float | None = None

    @model_validator(mode="after")
    def _validate_bounds(self) -> ConstantCurrentStimulus:
        if not math.isfinite(self.current_a):
            raise ValueError("current_a must be finite")
        if not math.isfinite(self.start_s) or self.start_s < 0.0:
            raise ValueError("start_s must be finite and >= 0")
        if self.end_s is not None and (not math.isfinite(self.end_s) or self.end_s <= self.start_s):
            raise ValueError("end_s must be strictly greater than start_s")
        return self


class PoissonRateStimulus(BaseModel):
    """Time-bounded Poisson spike train input delivered to target membrane potential."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["poisson_rate"] = "poisson_rate"
    target_neuron_ids: tuple[str, ...] = Field(min_length=1)
    rate_hz: float
    weight_v: float
    start_s: float = 0.0
    end_s: float | None = None
    disable_refractory: bool = True

    @model_validator(mode="after")
    def _validate_bounds(self) -> PoissonRateStimulus:
        if not math.isfinite(self.rate_hz) or self.rate_hz < 0.0:
            raise ValueError("rate_hz must be finite and >= 0")
        if not math.isfinite(self.weight_v) or self.weight_v < 0.0:
            raise ValueError("weight_v must be finite and >= 0")
        if not math.isfinite(self.start_s) or self.start_s < 0.0:
            raise ValueError("start_s must be finite and >= 0")
        if self.end_s is not None and (not math.isfinite(self.end_s) or self.end_s <= self.start_s):
            raise ValueError("end_s must be strictly greater than start_s")
        return self


class EdgeGainModulation(BaseModel):
    """Non-mutating multiplicative gain applied to outgoing/incoming/both edges of target nodes."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["edge_gain_modulation"] = "edge_gain_modulation"
    target_neuron_ids: tuple[str, ...] = Field(min_length=1)
    scope: Literal["outgoing", "incoming", "both"] = "outgoing"
    factor: float

    @model_validator(mode="after")
    def _validate_factor(self) -> EdgeGainModulation:
        if not math.isfinite(self.factor) or self.factor < 0.0:
            raise ValueError("factor must be finite and non-negative")
        return self


class NeuronSilencing(BaseModel):
    """Explicitly typed synaptic silencing intervention (outgoing, incoming, or both zeroed)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["neuron_silencing"] = "neuron_silencing"
    target_neuron_ids: tuple[str, ...] = Field(min_length=1)
    mode: Literal["outgoing_zero", "incoming_zero", "both_zero"] = "outgoing_zero"


class EdgeMaskModulation(BaseModel):
    """Non-mutating pathway multiplier on edges from pre_neuron_ids to post_neuron_ids."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["edge_mask"] = "edge_mask"
    pre_neuron_ids: tuple[str, ...] = Field(min_length=1)
    post_neuron_ids: tuple[str, ...] = Field(min_length=1)
    factor: float = 0.0

    @model_validator(mode="after")
    def _validate_factor(self) -> EdgeMaskModulation:
        if not math.isfinite(self.factor) or self.factor < 0.0:
            raise ValueError("factor must be finite and non-negative")
        return self


class ShamIntervention(BaseModel):
    """Explicit no-op sham control intervention."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["sham"] = "sham"
    description: str = "sham_no_op"


InterventionSpec = (
    ConstantCurrentStimulus
    | PoissonRateStimulus
    | EdgeGainModulation
    | EdgeMaskModulation
    | NeuronSilencing
    | ShamIntervention
)


class ResolvedInterventionRecord(BaseModel):
    """Audit record describing exactly what an intervention affected during a run."""

    model_config = ConfigDict(frozen=True)

    order_index: int
    kind: str
    resolved_target_ids: tuple[str, ...]
    affected_edge_count: int
    parameter_delta: dict[str, float | str | bool]
    units: str
    start_s: float
    end_s: float | None


def validate_model_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate a candidate model specification mapping against LIFParameters (CPU reference)."""
    if not isinstance(spec, dict):
        raise ValueError("Model specification must be a JSON/YAML mapping")

    backend = spec.get("backend")
    if backend is not None and backend != "brian2_cpu":
        raise ValueError(
            f"Unsupported or unverified backend {backend!r}; CPU reference is 'brian2_cpu' "
            "(accelerated GPU backends are Linux-only opt-in and unverified on this host)"
        )

    raw_params = spec.get("parameters")
    if raw_params is not None and not isinstance(raw_params, dict):
        raise ValueError("Model spec 'parameters' field must be a mapping")

    merged: dict[str, Any] = dict(raw_params) if raw_params is not None else dict(spec)
    if "id" in spec and "model_id" not in merged:
        merged["model_id"] = spec["id"]
    if "revision" in spec and "model_revision" not in merged:
        merged["model_revision"] = str(spec["revision"])
    for meta_key in ("backend", "id", "revision", "parameter_manifest_sha256", "schema_version"):
        if raw_params is None:
            merged.pop(meta_key, None)

    unknown_keys = sorted(set(merged) - set(LIFParameters.model_fields))
    if unknown_keys:
        raise ValueError(f"Unknown LIF model parameter field(s): {', '.join(unknown_keys)}")

    try:
        params = LIFParameters(**merged)
    except ValidationError as exc:
        raise ValueError(f"Invalid LIF model specification: {exc}") from exc

    computed_sha = params.canonical_sha256()
    declared_sha = spec.get("parameter_manifest_sha256")
    if declared_sha is not None:
        if str(declared_sha).strip().upper() == "UNRESOLVED":
            raise ValueError("parameter_manifest_sha256 cannot be UNRESOLVED")
        if str(declared_sha) != computed_sha:
            raise ValueError(
                f"parameter_manifest_sha256 mismatch: declared {declared_sha}, "
                f"computed {computed_sha}"
            )

    return {
        "valid": True,
        "model_id": params.model_id,
        "model_revision": params.model_revision,
        "parameter_manifest_sha256": computed_sha,
        "supported_on_cpu_reference": True,
        "gpu_verified": False,
        "parameters": params.model_dump(mode="json"),
    }
