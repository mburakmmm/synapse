"""SYNAPSE data ingestion, verified downloads, manifest validation, and source registry."""

from synapse_data.download import (
    ChecksumMismatchError,
    DownloadError,
    download_file_atomic,
    git_blob_sha1_file,
    md5_file,
    verify_upstream_checksum,
)
from synapse_data.flywire import (
    SHIU2024_MN9_ID,
    SHIU2024_SUGAR_GRN_IDS,
    FlyWireV630Adapter,
)
from synapse_data.ingest import (
    ALLOWED_NEUROTRANSMITTERS,
    ApprovalRequiredError,
    DataGateError,
    ingest_synthetic_fixture,
    sha256_file,
    validate_canonical_dataset,
    validate_manifest_schema,
)
from synapse_data.malecns import MaleCNSV1Adapter
from synapse_data.plans import FetchPlan, PlannedFile, SourceAdapter
from synapse_data.registry import SourceRegistry, build_default_registry

__all__ = [
    "ALLOWED_NEUROTRANSMITTERS",
    "SHIU2024_MN9_ID",
    "SHIU2024_SUGAR_GRN_IDS",
    "ApprovalRequiredError",
    "ChecksumMismatchError",
    "DataGateError",
    "DownloadError",
    "FetchPlan",
    "FlyWireV630Adapter",
    "MaleCNSV1Adapter",
    "PlannedFile",
    "SourceAdapter",
    "SourceRegistry",
    "build_default_registry",
    "download_file_atomic",
    "git_blob_sha1_file",
    "ingest_synthetic_fixture",
    "md5_file",
    "sha256_file",
    "validate_canonical_dataset",
    "validate_manifest_schema",
    "verify_upstream_checksum",
]
