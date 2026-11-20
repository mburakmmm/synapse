"""Janelia MaleCNS v1.0 flat-connectome adapter (CC-BY-4.0, approval-gated bulk fetch)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl
import pyarrow.feather as pa_feather  # type: ignore[import-untyped]
import pyarrow.ipc as pa_ipc  # type: ignore[import-untyped]

from synapse_data.download import download_file_atomic, verify_upstream_checksum
from synapse_data.ingest import (
    ADAPTER_VERSION,
    ApprovalRequiredError,
    DataGateError,
    sha256_file,
    validate_canonical_dataset,
)
from synapse_data.plans import FetchPlan, PlannedFile

MALECNS_GCS_BASE = (
    "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"
)
ANNOTATIONS_FILE = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
NEUROTRANSMITTERS_FILE = "body-neurotransmitters-male-cns-v1.0.feather"
WEIGHTS_FILE = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"

ANNOTATIONS_BYTES = 14483314
ANNOTATIONS_MD5 = "md5:50a7718770c57220f160ba4f431ab89e"
NEUROTRANSMITTERS_BYTES = 43282834
NEUROTRANSMITTERS_MD5 = "md5:3d842b12fe5c49eefade528d7dd24a1f"
WEIGHTS_BYTES = 1051241946
WEIGHTS_MD5 = "md5:f30e9dcca25cfd021bf1e7b3d975599e"

_NT_NORMALIZATION_MAP: dict[str, str] = {
    "acetylcholine": "ACH",
    "ach": "ACH",
    "gaba": "GABA",
    "glutamate": "GLUT",
    "glut": "GLUT",
    "dopamine": "DA",
    "da": "DA",
    "octopamine": "OCT",
    "oct": "OCT",
    "serotonin": "SER",
    "5-ht": "SER",
    "ser": "SER",
    "histamine": "HIST",
    "his": "HIST",
    "unknown": "UNKNOWN",
    "unclear": "UNKNOWN",
}

_ANNOTATION_COLS = ("bodyId", "type", "superclass", "class", "subclass", "somaSide", "status")


def _read_annotations_projected(ann_path: Path) -> pl.DataFrame:
    """Read MaleCNS annotations via PyArrow column projection, skipping dict(-1) statusLabel."""
    with pa_ipc.open_file(ann_path) as reader:
        available = set(reader.schema.names)
    if "bodyId" not in available:
        raise DataGateError("MaleCNS annotations Feather missing 'bodyId' column")
    selected = [col for col in _ANNOTATION_COLS if col in available]
    arrow_tbl = pa_feather.read_table(ann_path, columns=selected)
    df = pl.from_arrow(arrow_tbl)
    if not isinstance(df, pl.DataFrame):
        raise DataGateError("Expected DataFrame from PyArrow annotations table")
    return df.with_row_index("raw_row_index", offset=0)


class MaleCNSV1Adapter:
    """Adapter for adult male Drosophila CNS v1.0 (HHMI Janelia / Google Neural Mapping)."""

    dataset_id = "malecns_v1_0"

    def discover(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "release": "v1.0",
            "release_date": "2026-06-08",
            "is_synthetic_fixture": False,
            "source_uri": "https://male-cns.janelia.org/download/",
            "paper_doi": "10.1016/j.cell.2026.08.015",
            "license": "CC-BY-4.0",
            "verified_utc": "2026-11-20",
        }

    def plan(self) -> FetchPlan:
        return FetchPlan(
            dataset_id=self.dataset_id,
            release="v1.0",
            species="Drosophila melanogaster (adult male CNS: central brain, optic lobes, VNC)",
            license=(
                "CC-BY-4.0 (per male-cns.janelia.org/download/ and "
                "creativecommons.org/licenses/by/4.0/)"
            ),
            attribution=(
                "FlyEM (HHMI Janelia), University of Cambridge, MRC LMB, and Google Research"
            ),
            is_synthetic_fixture=False,
            credentials_required=False,
            approval_required=True,
            total_estimated_bytes=ANNOTATIONS_BYTES + NEUROTRANSMITTERS_BYTES + WEIGHTS_BYTES,
            files=(
                PlannedFile(
                    name=ANNOTATIONS_FILE,
                    role="neuron_annotations",
                    uri=f"{MALECNS_GCS_BASE}/{ANNOTATIONS_FILE}",
                    estimated_bytes=ANNOTATIONS_BYTES,
                    upstream_checksum=ANNOTATIONS_MD5,
                ),
                PlannedFile(
                    name=NEUROTRANSMITTERS_FILE,
                    role="neurotransmitter_predictions",
                    uri=f"{MALECNS_GCS_BASE}/{NEUROTRANSMITTERS_FILE}",
                    estimated_bytes=NEUROTRANSMITTERS_BYTES,
                    upstream_checksum=NEUROTRANSMITTERS_MD5,
                ),
                PlannedFile(
                    name=WEIGHTS_FILE,
                    role="connectivity_weights",
                    uri=f"{MALECNS_GCS_BASE}/{WEIGHTS_FILE}",
                    estimated_bytes=WEIGHTS_BYTES,
                    upstream_checksum=WEIGHTS_MD5,
                ),
            ),
            notes=(
                "Total core flat-connectome download is ~1.11 GB (1,109,008,094 bytes).",
                "Site-level tables (syn-points 12.7 GB, syn-partners 6.8 GB) excluded by default.",
                "Separate male specimen: node IDs must NEVER be pooled with FlyWire/FAFB.",
            ),
        )

    def fetch(self, target_dir: Path, *, approved: bool = False) -> Path:
        fetch_plan = self.plan()
        if not approved:
            raise ApprovalRequiredError(
                f"Download of biological dataset {self.dataset_id!r} "
                f"(release {fetch_plan.release}, "
                f"estimated_bytes={fetch_plan.total_estimated_bytes}) requires explicit user "
                "authorization per AGENTS.md sections 0, 6.1, and 17.5."
            )
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in fetch_plan.files:
            download_file_atomic(
                item.uri,
                target_dir / item.name,
                expected_bytes=item.estimated_bytes,
                upstream_checksum=item.upstream_checksum,
            )
        return target_dir

    def verify(self, raw_dir: Path) -> bool:
        for item in self.plan().files:
            path = raw_dir / item.name
            if not path.is_file():
                return False
            if item.estimated_bytes is not None and path.stat().st_size != item.estimated_bytes:
                return False
            if item.upstream_checksum is not None and not verify_upstream_checksum(
                path, item.upstream_checksum
            ):
                return False
        return True

    def normalize(
        self,
        raw_dir: Path,
        out_dir: Path,
        *,
        scope: Literal["annotated_bodies", "all_segments"] = "annotated_bodies",
        is_synthetic_fixture: bool = False,
        quarantine_invalid: bool = False,
    ) -> Path:
        """Normalize MaleCNS v1.0 Feather files into specimen-isolated canonical Parquet."""
        if scope not in ("annotated_bodies", "all_segments"):
            raise ValueError(f"Unsupported normalization scope {scope!r}")

        ann_path = raw_dir / ANNOTATIONS_FILE
        nt_path = raw_dir / NEUROTRANSMITTERS_FILE
        w_path = raw_dir / WEIGHTS_FILE
        for req in (ann_path, nt_path, w_path):
            if not req.is_file():
                raise DataGateError(f"Missing required MaleCNS raw Feather file: {req}")

        out_dir.mkdir(parents=True, exist_ok=True)
        curated_dir = out_dir / "curated"
        curated_dir.mkdir(parents=True, exist_ok=True)

        # 1. Read curated annotations via PyArrow projection
        ann_raw = _read_annotations_projected(ann_path)
        ann_typed = ann_raw.with_columns(pl.col("bodyId").cast(pl.Int64).alias("body_id"))
        ann_bad_mask = (
            pl.col("body_id").is_null()
            | (pl.col("body_id") < 0)
            | pl.col("body_id").is_duplicated()
        )
        invalid_ann = ann_typed.filter(ann_bad_mask)
        valid_ann = ann_typed.filter(~ann_bad_mask)

        # 2. Scan connectome weights lazily to avoid holding 151.8M unannotated rows in RAM
        w_lf = pl.scan_ipc(w_path)
        w_schema = w_lf.collect_schema()
        for col in ("body_pre", "body_post", "weight"):
            if col not in w_schema:
                raise DataGateError(f"MaleCNS weights Feather missing {col!r} column")

        w_indexed_lf = w_lf.with_row_index("raw_row_index", offset=0).with_columns(
            pl.col("body_pre").cast(pl.Int64).alias("pre_id"),
            pl.col("body_post").cast(pl.Int64).alias("post_id"),
            pl.col("weight").cast(pl.Int64).alias("synapse_count"),
        )
        w_bad_expr = (
            pl.col("pre_id").is_null()
            | (pl.col("pre_id") < 0)
            | pl.col("post_id").is_null()
            | (pl.col("post_id") < 0)
            | pl.col("synapse_count").is_null()
            | (pl.col("synapse_count") <= 0)
        )
        raw_w_stats = w_indexed_lf.select(
            pl.len().alias("raw_rows"),
            w_bad_expr.sum().alias("bad_rows"),
            pl.col("synapse_count").sum().alias("raw_total_synapses"),
        ).collect(engine="streaming")
        raw_w_rows = int(raw_w_stats["raw_rows"][0])
        bad_w_count = int(raw_w_stats["bad_rows"][0])
        raw_total_synapses = int(raw_w_stats["raw_total_synapses"][0]) if raw_w_rows > 0 else 0

        # 3. Read neurotransmitter table
        nt_raw = pl.read_ipc(nt_path).with_row_index("raw_row_index", offset=0)
        if "body" not in nt_raw.columns:
            raise DataGateError("MaleCNS neurotransmitters Feather missing 'body' column")
        nt_typed = nt_raw.with_columns(pl.col("body").cast(pl.Int64).alias("body_id"))
        nt_bad_mask = (
            pl.col("body_id").is_null()
            | (pl.col("body_id") < 0)
            | pl.col("body_id").is_duplicated()
        )
        invalid_nt = nt_typed.filter(nt_bad_mask)
        valid_nt = nt_typed.filter(~nt_bad_mask)

        q_frames: list[pl.DataFrame] = []
        if invalid_ann.height > 0:
            q_frames.append(
                invalid_ann.select(
                    pl.lit("annotations").alias("table"),
                    pl.col("raw_row_index").cast(pl.Int64),
                    pl.lit("null_negative_or_duplicate_bodyId").alias("reason"),
                    pl.struct([pl.col("body_id").cast(pl.String).alias("source_neuron_id")])
                    .struct.json_encode()
                    .alias("raw_record"),
                )
            )
        if bad_w_count > 0:
            invalid_w_df = (
                w_indexed_lf.filter(w_bad_expr)
                .select(
                    pl.lit("connections").alias("table"),
                    pl.col("raw_row_index").cast(pl.Int64),
                    pl.lit("invalid_body_or_non_positive_weight").alias("reason"),
                    pl.struct(
                        [
                            pl.col("pre_id").cast(pl.String).alias("pre_source_id"),
                            pl.col("post_id").cast(pl.String).alias("post_source_id"),
                            "synapse_count",
                        ]
                    )
                    .struct.json_encode()
                    .alias("raw_record"),
                )
                .collect(engine="streaming")
            )
            q_frames.append(invalid_w_df)
        if invalid_nt.height > 0:
            q_frames.append(
                invalid_nt.select(
                    pl.lit("neurotransmitters").alias("table"),
                    pl.col("raw_row_index").cast(pl.Int64),
                    pl.lit("null_negative_or_duplicate_body").alias("reason"),
                    pl.struct([pl.col("body_id").cast(pl.String).alias("source_neuron_id")])
                    .struct.json_encode()
                    .alias("raw_record"),
                )
            )

        q_path = out_dir / "quarantine.parquet"
        if q_frames:
            q_df = pl.concat(q_frames)
            q_df.write_parquet(q_path)
            n_quarantined = q_df.height
            if not quarantine_invalid:
                raise DataGateError(
                    f"MaleCNS v1.0 ingest quarantined {n_quarantined} invalid record(s) into "
                    f"{q_path}; failing closed because quarantine_invalid=False"
                )
        else:
            pl.DataFrame(
                schema={
                    "table": pl.String,
                    "raw_row_index": pl.Int64,
                    "reason": pl.String,
                    "raw_record": pl.String,
                }
            ).write_parquet(q_path)
            n_quarantined = 0

        # 4. Apply scope filter lazily BEFORE collecting edges
        valid_w_lf = w_indexed_lf.filter(~w_bad_expr).select("pre_id", "post_id", "synapse_count")
        ann_keys_lf = valid_ann.select(pl.col("body_id").alias("_k")).lazy()

        if scope == "annotated_bodies":
            scoped_w_lf = valid_w_lf.join(
                ann_keys_lf, left_on="pre_id", right_on="_k", how="semi"
            ).join(ann_keys_lf, left_on="post_id", right_on="_k", how="semi")
            valid_w_df = scoped_w_lf.collect(engine="streaming")
            all_body_ids = valid_ann.select("body_id").unique()
        else:
            valid_w_df = valid_w_lf.collect(engine="streaming")
            all_body_ids = pl.concat(
                [
                    valid_ann.select("body_id"),
                    valid_w_df.select(pl.col("pre_id").alias("body_id")),
                    valid_w_df.select(pl.col("post_id").alias("body_id")),
                    valid_nt.select("body_id"),
                ]
            ).unique()

        ann_cols = {
            c: valid_ann[c].dtype
            for c in ("type", "superclass", "class", "subclass", "somaSide", "status")
            if c in valid_ann.columns
        }
        ann_subset_cols = ["body_id", *list(ann_cols.keys())]
        neurons_joined = all_body_ids.join(
            valid_ann.select(ann_subset_cols).with_columns(pl.lit(True).alias("_in_ann")),
            on="body_id",
            how="left",
        )
        default_status = (
            pl.lit("synthetic_fixture")
            if is_synthetic_fixture
            else pl.when(pl.col("_in_ann").fill_null(False))
            .then(
                pl.col("status").fill_null("malecns_v1_annotated")
                if "status" in ann_cols
                else pl.lit("malecns_v1_annotated")
            )
            .otherwise(pl.lit("unannotated_segment_from_weights"))
        )
        neurons_out = neurons_joined.select(
            pl.lit(self.dataset_id).alias("dataset_id"),
            pl.lit("v1.0").alias("release"),
            pl.lit("malecns_male_01").alias("specimen_id"),
            pl.col("body_id").cast(pl.String).alias("source_neuron_id"),
            (pl.col("type") if "type" in ann_cols else pl.lit(None, dtype=pl.String)).alias(
                "cell_type"
            ),
            (
                pl.col("superclass") if "superclass" in ann_cols else pl.lit(None, dtype=pl.String)
            ).alias("superclass"),
            (pl.col("somaSide") if "somaSide" in ann_cols else pl.lit(None, dtype=pl.String)).alias(
                "soma_side"
            ),
            default_status.alias("annotation_status"),
            pl.lit("janelia:male-cns-v1.0").alias("provenance"),
        )

        # 5. Canonical connections table (Int64 group_by, cast to String only on final write)
        scoped_valid_count = valid_w_df.height
        grouped_w = valid_w_df.group_by(["pre_id", "post_id"], maintain_order=False).agg(
            pl.col("synapse_count").sum().cast(pl.Int64).alias("synapse_count")
        )
        duplicate_pairs_collapsed = scoped_valid_count - grouped_w.height
        self_loops = int(grouped_w.filter(pl.col("pre_id") == pl.col("post_id")).height)

        conns_out = grouped_w.select(
            pl.lit(self.dataset_id).alias("dataset_id"),
            pl.lit("v1.0").alias("release"),
            pl.lit("malecns_male_01").alias("specimen_id"),
            pl.col("pre_id").cast(pl.String).alias("pre_source_id"),
            pl.col("post_id").cast(pl.String).alias("post_source_id"),
            pl.col("synapse_count"),
            pl.lit(None, dtype=pl.String).alias("region"),
            pl.lit(None, dtype=pl.Float64).alias("confidence"),
            pl.lit("sum").alias("aggregation_policy"),
        )

        # 6. Canonical neurotransmitters mapped cleanly without inventing missing values
        has_cons = "consensus_nt" in valid_nt.columns
        has_pred = "predicted_nt" in valid_nt.columns
        has_conf = "predicted_nt_confidence" in valid_nt.columns

        raw_nt_expr = (
            pl.coalesce(
                [
                    c
                    for c in (
                        pl.col("consensus_nt") if has_cons else None,
                        pl.col("predicted_nt") if has_pred else None,
                    )
                    if c is not None
                ]
            )
            if (has_cons or has_pred)
            else pl.lit(None, dtype=pl.String)
        )
        nt_prepared = valid_nt.select(
            pl.col("body_id"),
            raw_nt_expr.alias("raw_label"),
            (
                pl.col("predicted_nt_confidence").cast(pl.Float64)
                if has_conf
                else pl.lit(None, dtype=pl.Float64)
            ).alias("raw_conf"),
            (
                pl.when(pl.col("consensus_nt").is_not_null())
                .then(pl.lit("malecns_v1_consensus_or_predicted"))
                .otherwise(pl.lit("malecns_v1_predicted"))
                if has_cons
                else pl.lit("malecns_v1_predicted")
            ).alias("pred_method"),
        ).with_columns(
            pl.col("raw_label")
            .str.strip_chars()
            .str.to_lowercase()
            .replace_strict(_NT_NORMALIZATION_MAP, default="UNKNOWN")
            .fill_null("UNKNOWN")
            .alias("mapped_nt")
        )

        nts_out = (
            all_body_ids.join(nt_prepared, on="body_id", how="left")
            .with_columns(
                pl.col("mapped_nt").fill_null("UNKNOWN").alias("neurotransmitter"),
                pl.col("pred_method")
                .fill_null("malecns_v1_missing_record")
                .alias("prediction_method"),
                pl.when(pl.col("raw_label").is_null())
                .then(pl.lit("missing_nt_prediction"))
                .when(pl.col("mapped_nt") == "UNKNOWN")
                .then(pl.concat_str([pl.lit("unknown_or_unmapped:"), pl.col("raw_label")]))
                .otherwise(pl.lit("observed"))
                .alias("missingness"),
            )
            .select(
                pl.lit(self.dataset_id).alias("dataset_id"),
                pl.lit("v1.0").alias("release"),
                pl.lit("malecns_male_01").alias("specimen_id"),
                pl.col("body_id").cast(pl.String).alias("source_neuron_id"),
                pl.col("neurotransmitter"),
                pl.col("raw_label").alias("raw_neurotransmitter_label"),
                pl.col("prediction_method"),
                pl.col("raw_conf").alias("confidence"),
                pl.col("missingness"),
            )
        )

        total_synapses = int(conns_out["synapse_count"].sum()) if conns_out.height > 0 else 0
        excluded_fragment_edges = (raw_w_rows - bad_w_count) - scoped_valid_count
        excluded_fragment_synapses = raw_total_synapses - total_synapses

        nt_counts = {
            row["neurotransmitter"]: int(row["len"])
            for row in nts_out.group_by("neurotransmitter").len().iter_rows(named=True)
        }
        status_counts = {
            str(row["annotation_status"]): int(row["len"])
            for row in neurons_out.group_by("annotation_status").len().iter_rows(named=True)
        }

        neurons_pq = curated_dir / "neurons.parquet"
        conns_pq = curated_dir / "connections.parquet"
        nts_pq = curated_dir / "neurotransmitters.parquet"
        qc_path = out_dir / "qc_summary.json"

        neurons_out.write_parquet(neurons_pq)
        conns_out.write_parquet(conns_pq)
        nts_out.write_parquet(nts_pq)

        qc_summary = {
            "dataset_id": self.dataset_id,
            "release": "v1.0",
            "normalization_scope": scope,
            "is_synthetic_fixture": is_synthetic_fixture,
            "raw_annotation_rows": ann_raw.height,
            "annotated_neuron_count": valid_ann.height,
            "canonical_neuron_count": neurons_out.height,
            "raw_connection_rows": raw_w_rows,
            "raw_total_synapse_count": raw_total_synapses,
            "canonical_connection_count": conns_out.height,
            "duplicate_pairs_collapsed": duplicate_pairs_collapsed,
            "self_loop_count": self_loops,
            "total_synapse_count": total_synapses,
            "excluded_unannotated_fragment_edges": excluded_fragment_edges,
            "excluded_unannotated_fragment_synapses": excluded_fragment_synapses,
            "quarantined_rows": n_quarantined,
            "annotation_status_breakdown": status_counts,
            "neurotransmitter_breakdown": nt_counts,
        }
        qc_path.write_text(json.dumps(qc_summary, indent=2, sort_keys=True), encoding="utf-8")

        parent_raw_files = [
            {
                "name": ANNOTATIONS_FILE,
                "role": "neuron_annotations",
                "uri": f"{MALECNS_GCS_BASE}/{ANNOTATIONS_FILE}",
                "bytes": ann_path.stat().st_size,
                "sha256": sha256_file(ann_path),
                "upstream_checksum": None if is_synthetic_fixture else ANNOTATIONS_MD5,
            },
            {
                "name": NEUROTRANSMITTERS_FILE,
                "role": "neurotransmitter_predictions",
                "uri": f"{MALECNS_GCS_BASE}/{NEUROTRANSMITTERS_FILE}",
                "bytes": nt_path.stat().st_size,
                "sha256": sha256_file(nt_path),
                "upstream_checksum": None if is_synthetic_fixture else NEUROTRANSMITTERS_MD5,
            },
            {
                "name": WEIGHTS_FILE,
                "role": "connectivity_weights",
                "uri": f"{MALECNS_GCS_BASE}/{WEIGHTS_FILE}",
                "bytes": w_path.stat().st_size,
                "sha256": sha256_file(w_path),
                "upstream_checksum": None if is_synthetic_fixture else WEIGHTS_MD5,
            },
        ]

        files_entries = [
            {
                "path": p.relative_to(out_dir).as_posix(),
                "role": role,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "upstream_checksum": None,
            }
            for p, role in (
                (neurons_pq, "canonical_neurons"),
                (conns_pq, "canonical_connections"),
                (nts_pq, "canonical_neurotransmitters"),
                (q_path, "quarantine_records"),
                (qc_path, "qc_summary"),
            )
        ]

        manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "dataset_id": self.dataset_id,
            "release": "v1.0",
            "species": "Drosophila melanogaster",
            "life_stage": "adult",
            "sex": "male",
            "specimen_id": "malecns_male_01",
            "coverage": (
                "Synthetic schema fixture"
                if is_synthetic_fixture
                else (
                    f"Adult male CNS ({scope}: {neurons_out.height} bodies, "
                    f"{conns_out.height} edges, {total_synapses} synapses)"
                )
            ),
            "source_uri": "https://male-cns.janelia.org/download/",
            "source_reference": "MaleCNS v1.0 (doi:10.1016/j.cell.2026.08.015)",
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "license": "CC-BY-4.0",
            "attribution": (
                "FlyEM (HHMI Janelia), University of Cambridge, MRC LMB, and Google Research"
            ),
            "is_synthetic_fixture": is_synthetic_fixture,
            "files": files_entries,
            "parent_raw_files": parent_raw_files,
            "adapter_version": ADAPTER_VERSION,
            "transforms": [
                {
                    "step": "normalize_malecns_annotations",
                    "description": (
                        "Read Arrow Feather v1.0 annotations via PyArrow projection, cast bodyId "
                        "to String, and enforce uniqueness"
                    ),
                    "input_rows": ann_raw.height,
                    "output_rows": neurons_out.height,
                    "rejected_rows": invalid_ann.height,
                },
                {
                    "step": f"normalize_malecns_weights_{scope}",
                    "description": (
                        f"Validate positive integer synapse weights under scope={scope!r} "
                        f"(excluded_unannotated_fragment_edges={excluded_fragment_edges}, "
                        f"raw_total_synapse_count={raw_total_synapses})"
                    ),
                    "input_rows": raw_w_rows,
                    "output_rows": conns_out.height,
                    "rejected_rows": bad_w_count + excluded_fragment_edges,
                },
                {
                    "step": "normalize_malecns_neurotransmitters",
                    "description": "Map consensus/predicted NT strings to canonical vocabulary",
                    "input_rows": nt_raw.height,
                    "output_rows": nts_out.height,
                    "rejected_rows": invalid_nt.height,
                },
            ],
            "quality_report": {
                "passed": True,
                "neuron_count": neurons_out.height,
                "connection_count": conns_out.height,
                "total_synapse_count": total_synapses,
                "quarantined_rows": n_quarantined,
                "checks": {
                    "unique_neuron_ids": True,
                    "foreign_keys_valid": True,
                    "positive_synapse_counts": True,
                },
            },
            "known_limitations": [
                "Separate specimen reconstruction from FlyWire/FAFB; node IDs cannot be pooled.",
                (
                    f"Normalization scope={scope!r}: excluded {excluded_fragment_edges} edges "
                    f"({excluded_fragment_synapses} synapses) involving unannotated segments "
                    f"outside body-annotations (raw total: {raw_w_rows} edges, "
                    f"{raw_total_synapses} synapses)."
                    if scope == "annotated_bodies"
                    else "All segmented bodies included; unannotated segments lack cell typing."
                ),
                "Minconf-0.5 flat connectome excludes site-level coordinates "
                "unless fetched separately.",
                "One male and one female specimen cannot establish "
                "population-level sex differences.",
            ],
            "unknown_field_reasons": {
                "region": "minconf-0.5 flat connectome weights table omits neuropil breakdown.",
                "confidence": (
                    "connectome-weights table filters >=0.5 confidence without edge score."
                ),
            },
        }

        manifest_path = out_dir / "dataset_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        validate_canonical_dataset(out_dir)
        return manifest_path

    def validate(self, dataset_dir: Path) -> dict[str, Any]:
        return validate_canonical_dataset(dataset_dir)
