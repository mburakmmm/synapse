"""Dataset ingestion, quarantine handling, canonical Parquet export, and data gates."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import polars as pl

ADAPTER_VERSION = "0.2.0-phase1"
ALLOWED_NEUROTRANSMITTERS: frozenset[str] = frozenset(
    {
        "ACH",
        "GABA",
        "GLUT",
        "DA",
        "OCT",
        "SER",
        "HIST",
        "UNKNOWN",
        "EXCITATORY_SIGN",
        "INHIBITORY_SIGN",
        "CONFLICTING_SIGN",
    }
)


class DataGateError(ValueError):
    """Raised when dataset ingestion or validation fails a mandatory data gate."""


class ApprovalRequiredError(PermissionError):
    """Raised when a biological dataset fetch is attempted without explicit approval."""


def default_dataset_schema_path() -> Path:
    """Locate ``schemas/dataset_manifest.v1.schema.json`` relative to repository root."""
    return Path(__file__).resolve().parents[2] / "schemas" / "dataset_manifest.v1.schema.json"


def sha256_file(path: Path) -> str:
    """Compute streaming SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest_schema(
    manifest: dict[str, Any],
    schema_path: Path | None = None,
) -> None:
    """Validate a dataset manifest dictionary against the Draft 2020-12 JSON Schema."""
    resolved_schema = default_dataset_schema_path() if schema_path is None else schema_path
    schema = json.loads(resolved_schema.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        raise DataGateError(f"Dataset manifest schema violation: {first.message}")


def _write_quarantine(out_dir: Path, rows: list[dict[str, str]]) -> Path:
    q_path = out_dir / "quarantine.parquet"
    if rows:
        q_df = pl.DataFrame(rows)
    else:
        q_df = pl.DataFrame(
            schema={
                "table": pl.String,
                "row_index": pl.Int64,
                "raw_record": pl.String,
                "reason": pl.String,
            }
        )
    q_df.write_parquet(q_path)
    return q_path


def ingest_synthetic_fixture(
    raw_dir: Path,
    out_dir: Path,
    *,
    schema_path: Path | None = None,
    quarantine_invalid: bool = False,
) -> Path:
    """Ingest, verify, normalize to canonical Parquet, and gate-check a synthetic fixture."""
    meta_path = raw_dir / "source_metadata.json"
    neurons_csv = raw_dir / "neurons.csv"
    connections_csv = raw_dir / "connections.csv"
    nt_csv = raw_dir / "neurotransmitters.csv"

    for required in (meta_path, neurons_csv, connections_csv, nt_csv):
        if not required.is_file():
            raise DataGateError(f"Missing required fixture input file: {required}")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if not metadata.get("is_synthetic_fixture", False):
        raise DataGateError(
            "ingest_synthetic_fixture requires source_metadata.json with is_synthetic_fixture=true"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_copy_dir = out_dir / "raw"
    raw_copy_dir.mkdir(parents=True, exist_ok=True)

    # Preserve read-only raw lineage copies before transformation
    raw_hashes: dict[str, tuple[int, str]] = {}
    for src in (meta_path, neurons_csv, connections_csv, nt_csv):
        dst = raw_copy_dir / src.name
        shutil.copy2(src, dst)
        raw_hashes[f"raw/{src.name}"] = (dst.stat().st_size, sha256_file(dst))

    quarantine_rows: list[dict[str, str]] = []

    # 1. Load & normalize neurons with explicit String IDs (lossless 64-bit preservation)
    df_neurons_raw = pl.read_csv(
        neurons_csv,
        schema_overrides={
            "source_neuron_id": pl.String,
            "role_label": pl.String,
            "region": pl.String,
            "annotation_status": pl.String,
            "provenance": pl.String,
        },
    )
    seen_ids: set[str] = set()
    valid_neurons: list[dict[str, str]] = []
    for idx, row in enumerate(df_neurons_raw.iter_rows(named=True)):
        nid = (row.get("source_neuron_id") or "").strip()
        ann_status = (row.get("annotation_status") or "").strip()
        if not nid:
            quarantine_rows.append(
                {
                    "table": "neurons",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": "empty source_neuron_id",
                }
            )
            continue
        if nid in seen_ids:
            quarantine_rows.append(
                {
                    "table": "neurons",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"duplicate source_neuron_id {nid}",
                }
            )
            continue
        if ann_status != "synthetic_fixture":
            quarantine_rows.append(
                {
                    "table": "neurons",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": (
                        "synthetic fixture neuron missing annotation_status='synthetic_fixture'"
                    ),
                }
            )
            continue
        seen_ids.add(nid)
        valid_neurons.append(
            {
                "dataset_id": str(metadata["dataset_id"]),
                "release": str(metadata["release"]),
                "specimen_id": str(metadata["specimen_id"]),
                "source_neuron_id": nid,
                "role_label": str(row.get("role_label") or ""),
                "region": str(row.get("region") or ""),
                "annotation_status": ann_status,
                "provenance": str(row.get("provenance") or ""),
            }
        )

    # 2. Load & normalize connections
    df_conn_raw = pl.read_csv(
        connections_csv,
        schema_overrides={
            "pre_source_id": pl.String,
            "post_source_id": pl.String,
            "synapse_count": pl.Int64,
            "region": pl.String,
            "confidence": pl.Float64,
            "aggregation_policy": pl.String,
        },
    )
    valid_conns: list[dict[str, Any]] = []
    for idx, row in enumerate(df_conn_raw.iter_rows(named=True)):
        pre = (row.get("pre_source_id") or "").strip()
        post = (row.get("post_source_id") or "").strip()
        count = row.get("synapse_count")
        conf = row.get("confidence")
        if pre not in seen_ids or post not in seen_ids:
            quarantine_rows.append(
                {
                    "table": "connections",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"dangling foreign key ({pre!r} -> {post!r})",
                }
            )
            continue
        if count is None or count <= 0:
            quarantine_rows.append(
                {
                    "table": "connections",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"non-positive synapse_count={count!r}",
                }
            )
            continue
        if conf is None or not math.isfinite(float(conf)) or not (0.0 <= float(conf) <= 1.0):
            quarantine_rows.append(
                {
                    "table": "connections",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"invalid confidence={conf!r}",
                }
            )
            continue
        valid_conns.append(
            {
                "dataset_id": str(metadata["dataset_id"]),
                "release": str(metadata["release"]),
                "specimen_id": str(metadata["specimen_id"]),
                "pre_source_id": pre,
                "post_source_id": post,
                "synapse_count": int(count),
                "region": str(row.get("region") or ""),
                "confidence": float(conf),
                "aggregation_policy": str(row.get("aggregation_policy") or "sum"),
            }
        )

    # 3. Load & normalize neurotransmitters
    df_nt_raw = pl.read_csv(
        nt_csv,
        schema_overrides={
            "source_neuron_id": pl.String,
            "neurotransmitter": pl.String,
            "prediction_method": pl.String,
            "confidence": pl.Float64,
            "missingness": pl.String,
        },
    )
    valid_nts: list[dict[str, Any]] = []
    seen_nt_ids: set[str] = set()
    for idx, row in enumerate(df_nt_raw.iter_rows(named=True)):
        nid = (row.get("source_neuron_id") or "").strip()
        nt = (row.get("neurotransmitter") or "UNKNOWN").strip().upper()
        if nid not in seen_ids or nid in seen_nt_ids:
            quarantine_rows.append(
                {
                    "table": "neurotransmitters",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"unknown or duplicate neuron_id {nid!r}",
                }
            )
            continue
        if nt not in ALLOWED_NEUROTRANSMITTERS:
            quarantine_rows.append(
                {
                    "table": "neurotransmitters",
                    "row_index": str(idx),
                    "raw_record": json.dumps(row, default=str),
                    "reason": f"disallowed neurotransmitter category {nt!r}",
                }
            )
            continue
        seen_nt_ids.add(nid)
        valid_nts.append(
            {
                "dataset_id": str(metadata["dataset_id"]),
                "release": str(metadata["release"]),
                "specimen_id": str(metadata["specimen_id"]),
                "source_neuron_id": nid,
                "neurotransmitter": nt,
                "prediction_method": str(row.get("prediction_method") or ""),
                "confidence": float(row["confidence"]),
                "missingness": str(row.get("missingness") or "observed"),
            }
        )

    quarantine_path = _write_quarantine(out_dir, quarantine_rows)
    if quarantine_rows and not quarantine_invalid:
        raise DataGateError(
            f"Ingest quarantined {len(quarantine_rows)} invalid record(s) into {quarantine_path}; "
            "failing closed because quarantine_invalid=False"
        )

    curated_dir = out_dir / "curated"
    curated_dir.mkdir(parents=True, exist_ok=True)
    neurons_pq = curated_dir / "neurons.parquet"
    connections_pq = curated_dir / "connections.parquet"
    nt_pq = curated_dir / "neurotransmitters.parquet"

    pl.DataFrame(valid_neurons).write_parquet(neurons_pq)
    pl.DataFrame(valid_conns).write_parquet(connections_pq)
    pl.DataFrame(valid_nts).write_parquet(nt_pq)

    files_entries: list[dict[str, Any]] = [
        {
            "path": rel,
            "role": "raw_source",
            "bytes": size_bytes,
            "sha256": digest,
            "upstream_checksum": None,
        }
        for rel, (size_bytes, digest) in sorted(raw_hashes.items())
    ]
    for pq_path, role in (
        (neurons_pq, "canonical_neurons"),
        (connections_pq, "canonical_connections"),
        (nt_pq, "canonical_neurotransmitters"),
        (quarantine_path, "quarantine_records"),
    ):
        files_entries.append(
            {
                "path": pq_path.relative_to(out_dir).as_posix(),
                "role": role,
                "bytes": pq_path.stat().st_size,
                "sha256": sha256_file(pq_path),
                "upstream_checksum": None,
            }
        )

    total_synapses = sum(int(r["synapse_count"]) for r in valid_conns)
    n_q_neurons = sum(1 for r in quarantine_rows if r["table"] == "neurons")
    n_q_conns = sum(1 for r in quarantine_rows if r["table"] == "connections")
    n_q_nts = sum(1 for r in quarantine_rows if r["table"] == "neurotransmitters")

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_id": metadata["dataset_id"],
        "release": metadata["release"],
        "species": metadata["species"],
        "life_stage": metadata["life_stage"],
        "sex": metadata["sex"],
        "specimen_id": metadata["specimen_id"],
        "coverage": metadata["coverage"],
        "source_uri": metadata["source_uri"],
        "source_reference": metadata["source_reference"],
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "license": metadata["license"],
        "attribution": metadata["attribution"],
        "is_synthetic_fixture": True,
        "files": files_entries,
        "adapter_version": ADAPTER_VERSION,
        "transforms": [
            {
                "step": "normalize_neurons",
                "description": "Cast 64-bit source_neuron_id as UTF-8 String and verify uniqueness",
                "input_rows": df_neurons_raw.height,
                "output_rows": len(valid_neurons),
                "rejected_rows": n_q_neurons,
            },
            {
                "step": "normalize_connections",
                "description": (
                    "Validate pre->post foreign keys, positive synapse_count, finite confidence"
                ),
                "input_rows": df_conn_raw.height,
                "output_rows": len(valid_conns),
                "rejected_rows": n_q_conns,
            },
            {
                "step": "normalize_neurotransmitters",
                "description": (
                    "Validate allowed categorical neurotransmitter vocabulary and foreign keys"
                ),
                "input_rows": df_nt_raw.height,
                "output_rows": len(valid_nts),
                "rejected_rows": n_q_nts,
            },
        ],
        "quality_report": {
            "passed": True,
            "neuron_count": len(valid_neurons),
            "connection_count": len(valid_conns),
            "total_synapse_count": total_synapses,
            "quarantined_rows": len(quarantine_rows),
            "checks": {
                "unique_neuron_ids": True,
                "foreign_keys_valid": True,
                "positive_synapse_counts": True,
                "finite_numeric_fields": True,
                "synthetic_fixture_tagged": True,
            },
        },
        "known_limitations": metadata["known_limitations"],
        "unknown_field_reasons": metadata["unknown_field_reasons"],
    }

    manifest_path = out_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    validate_canonical_dataset(out_dir, schema_path=schema_path)
    return manifest_path


def validate_canonical_dataset(
    dataset_dir: Path,
    *,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed validation of canonical Parquet dataset tables and manifest integrity."""
    manifest_path = dataset_dir / "dataset_manifest.json"
    if not manifest_path.is_file():
        raise DataGateError(f"Missing dataset_manifest.json in {dataset_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest_schema(manifest, schema_path=schema_path)

    for entry in manifest["files"]:
        file_path = (dataset_dir / entry["path"]).resolve()
        if not file_path.is_relative_to(dataset_dir.resolve()):
            raise DataGateError(f"Path traversal detected in manifest file entry: {entry['path']}")
        if not file_path.is_file():
            raise DataGateError(f"Manifest-declared file missing: {file_path}")
        actual_sha = sha256_file(file_path)
        if actual_sha != entry["sha256"]:
            raise DataGateError(
                f"Checksum mismatch for {entry['path']}: "
                f"expected {entry['sha256']}, got {actual_sha}"
            )

    neurons_df = pl.read_parquet(dataset_dir / "curated" / "neurons.parquet")
    conns_pq = dataset_dir / "curated" / "connections.parquet"
    nts_df = pl.read_parquet(dataset_dir / "curated" / "neurotransmitters.parquet")

    if neurons_df.height == 0:
        raise DataGateError("Canonical neurons table is empty")

    if neurons_df.schema.get("source_neuron_id") != pl.String:
        raise DataGateError("Canonical neurons.source_neuron_id must have String dtype")
    if (
        neurons_df["source_neuron_id"].null_count() > 0
        or (neurons_df["source_neuron_id"].str.len_chars() == 0).any()
    ):
        raise DataGateError("Canonical neurons table contains null or empty source_neuron_id")
    if neurons_df["source_neuron_id"].n_unique() != neurons_df.height:
        raise DataGateError("Duplicate source_neuron_id in canonical neurons table")

    if manifest["is_synthetic_fixture"]:
        statuses = set(neurons_df["annotation_status"].unique().to_list())
        if statuses != {"synthetic_fixture"}:
            raise DataGateError(
                "Synthetic fixture dataset must tag all neurons 'synthetic_fixture', "
                f"got {statuses}"
            )

    neuron_keys = neurons_df.select(pl.col("source_neuron_id"))
    neuron_keys_lazy = neuron_keys.lazy()

    conns_lf = pl.scan_parquet(conns_pq)
    conns_schema = conns_lf.collect_schema()
    conn_stats = conns_lf.select(
        pl.len().alias("row_count"),
        pl.col("synapse_count").sum().alias("total_synapses"),
        (pl.col("synapse_count").is_null() | (pl.col("synapse_count") <= 0))
        .sum()
        .alias("bad_syn_count"),
        (
            (
                pl.col("confidence").is_not_null()
                & (
                    ~pl.col("confidence").is_finite()
                    | (pl.col("confidence") < 0.0)
                    | (pl.col("confidence") > 1.0)
                )
            ).sum()
            if "confidence" in conns_schema
            else pl.lit(0)
        ).alias("bad_conf"),
    ).collect(engine="streaming")

    conn_height = int(conn_stats["row_count"][0])
    actual_total_synapses = int(conn_stats["total_synapses"][0]) if conn_height > 0 else 0

    if conn_height > 0:
        if (
            conns_schema.get("pre_source_id") != pl.String
            or conns_schema.get("post_source_id") != pl.String
        ):
            raise DataGateError("Canonical connections IDs must have String dtype")
        if int(conn_stats["bad_syn_count"][0]) > 0:
            raise DataGateError("Canonical connections contains null or non-positive synapse_count")
        bad_conf = int(conn_stats["bad_conf"][0])
        if bad_conf > 0:
            raise DataGateError(
                f"Canonical connections contains {bad_conf} non-finite or out-of-range confidence"
            )
        bad_pre = int(
            conns_lf.select(pl.col("pre_source_id").alias("source_neuron_id"))
            .join(neuron_keys_lazy, on="source_neuron_id", how="anti")
            .select(pl.len())
            .collect(engine="streaming")
            .item()
        )
        bad_post = int(
            conns_lf.select(pl.col("post_source_id").alias("source_neuron_id"))
            .join(neuron_keys_lazy, on="source_neuron_id", how="anti")
            .select(pl.len())
            .collect(engine="streaming")
            .item()
        )
        if bad_pre > 0 or bad_post > 0:
            raise DataGateError(
                f"Dangling foreign keys in canonical connections: pre={bad_pre}, post={bad_post}"
            )

    if nts_df.height > 0:
        if nts_df.schema.get("source_neuron_id") != pl.String:
            raise DataGateError("Canonical neurotransmitters.source_neuron_id must be String dtype")
        if nts_df["source_neuron_id"].n_unique() != nts_df.height:
            raise DataGateError("Duplicate source_neuron_id in canonical neurotransmitters table")
        bad_nt_fk = (
            nts_df.select("source_neuron_id")
            .join(neuron_keys, on="source_neuron_id", how="anti")
            .height
        )
        if bad_nt_fk > 0:
            raise DataGateError(f"Dangling foreign keys in neurotransmitters: {bad_nt_fk}")
        bad_nt_vocab = nts_df.filter(
            ~pl.col("neurotransmitter").is_in(sorted(ALLOWED_NEUROTRANSMITTERS))
        ).height
        if bad_nt_vocab > 0:
            raise DataGateError(
                f"Disallowed neurotransmitter category count={bad_nt_vocab} in canonical table"
            )
        if "confidence" in nts_df.columns:
            bad_nt_conf = nts_df.filter(
                pl.col("confidence").is_not_null()
                & (
                    ~pl.col("confidence").is_finite()
                    | (pl.col("confidence") < 0.0)
                    | (pl.col("confidence") > 1.0)
                )
            ).height
            if bad_nt_conf > 0:
                raise DataGateError(
                    f"Non-finite or out-of-range confidence in neurotransmitters: {bad_nt_conf}"
                )

    qr = manifest["quality_report"]
    if (
        qr["neuron_count"] != neurons_df.height
        or qr["connection_count"] != conn_height
        or qr["total_synapse_count"] != actual_total_synapses
    ):
        raise DataGateError("quality_report count reconciliation mismatch against Parquet tables")

    return manifest
