"""Source registry and fetch-plan adapters enforcing explicit dataset approvals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from synapse_data.flywire import FlyWireV630Adapter
from synapse_data.ingest import (
    ApprovalRequiredError,
    ingest_synthetic_fixture,
    validate_canonical_dataset,
)
from synapse_data.malecns import MaleCNSV1Adapter
from synapse_data.plans import FetchPlan, PlannedFile, SourceAdapter


class SyntheticFixtureAdapter:
    """Offline engineering fixture adapter for Phase 0 verification."""

    dataset_id = "synthetic_microcircuit_v1"

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self._fixture_dir = (
            Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "synthetic_microcircuit_v1"
            if fixture_dir is None
            else fixture_dir
        )

    def discover(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "release": "0.1.0-synth",
            "is_synthetic_fixture": True,
            "available_offline": self._fixture_dir.is_dir(),
            "source_uri": "local://tests/fixtures/synthetic_microcircuit_v1",
        }

    def plan(self) -> FetchPlan:
        files: list[PlannedFile] = []
        total_bytes = 0
        for name in (
            "neurons.csv",
            "connections.csv",
            "neurotransmitters.csv",
            "source_metadata.json",
        ):
            p = self._fixture_dir / name
            size = p.stat().st_size if p.is_file() else 0
            total_bytes += size
            files.append(
                PlannedFile(
                    name=name,
                    role="synthetic_fixture_input",
                    uri=f"local://tests/fixtures/synthetic_microcircuit_v1/{name}",
                    estimated_bytes=size,
                    upstream_checksum=None,
                )
            )
        return FetchPlan(
            dataset_id=self.dataset_id,
            release="0.1.0-synth",
            species="synthetic_engineering_fixture",
            license="Apache-2.0",
            attribution="SYNAPSE Contributors (synthetic engineering fixture)",
            is_synthetic_fixture=True,
            credentials_required=False,
            approval_required=False,
            total_estimated_bytes=total_bytes,
            files=tuple(files),
            notes=("Synthetic engineering fixture only; provides zero biological evidence.",),
        )

    def fetch(self, target_dir: Path, *, approved: bool = False) -> Path:
        del target_dir, approved
        if not self._fixture_dir.is_dir():
            raise FileNotFoundError(f"Fixture directory missing: {self._fixture_dir}")
        return self._fixture_dir

    def verify(self, raw_dir: Path) -> bool:
        required = (
            "neurons.csv",
            "connections.csv",
            "neurotransmitters.csv",
            "source_metadata.json",
        )
        return all((raw_dir / name).is_file() for name in required)

    def normalize(self, raw_dir: Path, out_dir: Path) -> Path:
        return ingest_synthetic_fixture(raw_dir, out_dir)

    def validate(self, dataset_dir: Path) -> dict[str, Any]:
        return validate_canonical_dataset(dataset_dir)


class ApprovalGatedBiologicalAdapter:
    """Source adapter for biological datasets that blocks fetch() without explicit authorization."""

    def __init__(self, fetch_plan: FetchPlan, discovery_info: dict[str, Any]) -> None:
        self.dataset_id = fetch_plan.dataset_id
        self._plan = fetch_plan
        self._discovery = discovery_info

    def discover(self) -> dict[str, Any]:
        return dict(self._discovery)

    def plan(self) -> FetchPlan:
        return self._plan

    def fetch(self, target_dir: Path, *, approved: bool = False) -> Path:
        del target_dir
        if not approved:
            raise ApprovalRequiredError(
                f"Download of biological dataset {self.dataset_id!r} "
                f"(release {self._plan.release}, "
                f"estimated_bytes={self._plan.total_estimated_bytes}) requires explicit user "
                "authorization per AGENTS.md sections 0, 6.1, and 17.5."
            )
        raise NotImplementedError(
            f"Approved downloader for {self.dataset_id!r} is not implemented in this phase."
        )

    def verify(self, raw_dir: Path) -> bool:
        del raw_dir
        return False

    def normalize(self, raw_dir: Path, out_dir: Path) -> Path:
        del raw_dir, out_dir
        raise NotImplementedError(
            f"Canonical normalization for {self.dataset_id!r} is not implemented in this phase."
        )

    def validate(self, dataset_dir: Path) -> dict[str, Any]:
        return validate_canonical_dataset(dataset_dir)


class SourceRegistry:
    """Registry of approved dataset adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters[adapter.dataset_id] = adapter

    def list_dataset_ids(self) -> list[str]:
        return sorted(self._adapters)

    def get(self, dataset_id: str) -> SourceAdapter:
        if dataset_id not in self._adapters:
            raise KeyError(f"Unknown dataset_id {dataset_id!r}; known: {self.list_dataset_ids()}")
        return self._adapters[dataset_id]


def build_default_registry() -> SourceRegistry:
    """Construct the source registry with synthetic and biological adapters."""
    registry = SourceRegistry()
    registry.register(SyntheticFixtureAdapter())
    registry.register(FlyWireV630Adapter())
    registry.register(MaleCNSV1Adapter())

    flywire_v783_plan = FetchPlan(
        dataset_id="flywire_fafb_v783",
        release="v783",
        species="Drosophila melanogaster (adult female brain)",
        license="cc-by-4.0",
        attribution="FlyWire Consortium (Zenodo record 10676866, doi:10.5281/zenodo.10676866)",
        is_synthetic_fixture=False,
        credentials_required=False,
        approval_required=True,
        total_estimated_bytes=1114168 + 852022274,
        files=(
            PlannedFile(
                name="proofread_root_ids_783.npy",
                role="neuron_ids",
                uri="https://zenodo.org/records/10676866/files/proofread_root_ids_783.npy",
                estimated_bytes=1114168,
                upstream_checksum="md5:e0e6c19732fd8c7a4e39a2d170105421",
            ),
            PlannedFile(
                name="proofread_connections_783.feather",
                role="connectivity_table",
                uri="https://zenodo.org/records/10676866/files/proofread_connections_783.feather",
                estimated_bytes=852022274,
                upstream_checksum="md5:f48f972d262323a102aed49af1396b8a",
            ),
        ),
        notes=(
            "Optional 9.49 GB flywire_synapses_783.feather excluded from default core LIF plan.",
            "Must NOT silently replace v630 for Shiu et al. 2024 historical reproduction.",
        ),
    )
    registry.register(
        ApprovalGatedBiologicalAdapter(
            flywire_v783_plan,
            {
                "dataset_id": "flywire_fafb_v783",
                "release": "v783",
                "zenodo_record": "10676866",
                "verified_utc": "2026-11-20",
                "status": "planned_awaiting_approval",
            },
        )
    )

    return registry
