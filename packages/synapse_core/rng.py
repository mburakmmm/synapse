"""Hierarchical deterministic seed derivation from master seed and run identifiers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

SEED_ALGORITHM = "sha256_hierarchical_v1"


@dataclass(frozen=True, slots=True)
class SeedRecord:
    """Provenance record for a simulation run's derived RNG seeds."""

    algorithm: str
    master_seed: int
    derived_seeds: dict[str, int]


def derive_seed(
    master_seed: int,
    *,
    experiment_id: str,
    condition_id: str,
    replicate_id: int,
    stream: str = "brian2",
) -> int:
    """Derive a deterministic 31-bit non-negative integer seed using SHA-256."""
    if isinstance(master_seed, bool) or not isinstance(master_seed, int) or master_seed < 0:
        raise ValueError(f"master_seed must be a non-negative integer, got {master_seed!r}")
    if isinstance(replicate_id, bool) or not isinstance(replicate_id, int) or replicate_id < 0:
        raise ValueError(f"replicate_id must be a non-negative integer, got {replicate_id!r}")
    if not experiment_id or not condition_id or not stream:
        raise ValueError("experiment_id, condition_id, and stream must be non-empty")

    payload = (
        f"{SEED_ALGORITHM}|{master_seed}|{experiment_id}|{condition_id}|{replicate_id}|{stream}"
    ).encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False) & 0x7FFFFFFF
