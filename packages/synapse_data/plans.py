"""Shared source adapter lifecycle protocol and fetch-plan data structures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PlannedFile:
    """Single file item in an explicit source fetch plan."""

    name: str
    role: str
    uri: str
    estimated_bytes: int | None
    upstream_checksum: str | None


@dataclass(frozen=True, slots=True)
class FetchPlan:
    """Explicit download and storage plan returned before any biological data transfer."""

    dataset_id: str
    release: str
    species: str
    license: str
    attribution: str
    is_synthetic_fixture: bool
    credentials_required: bool
    approval_required: bool
    total_estimated_bytes: int | None
    files: tuple[PlannedFile, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceAdapter(Protocol):
    """Lifecycle contract from AGENTS.md section 6.1."""

    dataset_id: str

    def discover(self) -> dict[str, Any]: ...

    def plan(self) -> FetchPlan: ...

    def fetch(self, target_dir: Path, *, approved: bool = False) -> Path: ...

    def verify(self, raw_dir: Path) -> bool: ...

    def normalize(self, raw_dir: Path, out_dir: Path) -> Path: ...

    def validate(self, dataset_dir: Path) -> dict[str, Any]: ...
