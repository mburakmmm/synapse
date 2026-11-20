"""FlyWire / FAFB v630 adapter for Shiu et al. (2024) historical reproduction."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from synapse_data.download import download_file_atomic, verify_upstream_checksum
from synapse_data.ingest import (
    ADAPTER_VERSION,
    ApprovalRequiredError,
    DataGateError,
    sha256_file,
    validate_canonical_dataset,
)
from synapse_data.plans import FetchPlan, PlannedFile

SHIU_COMMIT = "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"
SHIU_BASE_URI = f"https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/{SHIU_COMMIT}"
COMPLETENESS_FILENAME = "2023_03_23_completeness_630_final.csv"
CONNECTIVITY_FILENAME = "2023_03_23_connectivity_630_final.parquet"

COMPLETENESS_BYTES = 3057611
COMPLETENESS_BLOB_SHA1 = "git-blob-sha1:be745f0ce054308df21accc5c4b3883aa38498f9"
CONNECTIVITY_BYTES = 86630944
CONNECTIVITY_BLOB_SHA1 = "git-blob-sha1:8b4d9531bc0acbda7c2074ae577e6ac9e2fca166"

# Exact 21 sugar-sensing GRN IDs and MN9 motor neuron ID from example.ipynb (commit 91bdd1e)
SHIU2024_SUGAR_GRN_IDS: tuple[str, ...] = (
    "720575940624963786",
    "720575940630233916",
    "720575940637568838",
    "720575940638202345",
    "720575940617000768",
    "720575940630797113",
    "720575940632889389",
    "720575940621754367",
    "720575940621502051",
    "720575940640649691",
    "720575940639332736",
    "720575940616885538",
    "720575940639198653",
    "720575940620900446",
    "720575940617937543",
    "720575940632425919",
    "720575940633143833",
    "720575940612670570",
    "720575940628853239",
    "720575940629176663",
    "720575940611875570",
)
SHIU2024_MN9_ID = "720575940660219265"


def _write_empty_quarantine(out_dir: Path) -> Path:
    q_path = out_dir / "quarantine.parquet"
    pl.DataFrame(
        schema={
            "table": pl.String,
            "raw_row_index": pl.Int64,
            "reason": pl.String,
            "raw_record": pl.String,
        }
    ).write_parquet(q_path)
    return q_path


class FlyWireV630Adapter:
    """Adapter for FlyWire/FAFB v630 connectivity & completeness used in Shiu et al. (2024)."""

    dataset_id = "flywire_fafb_v630"

    def discover(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "release": "v630",
            "is_synthetic_fixture": False,
            "upstream_commit": SHIU_COMMIT,
            "source_uri": f"https://github.com/philshiu/Drosophila_brain_model/tree/{SHIU_COMMIT}",
            "verified_utc": "2026-11-20",
        }

    def plan(self) -> FetchPlan:
        return FetchPlan(
            dataset_id=self.dataset_id,
            release="v630",
            species="Drosophila melanogaster (adult female brain)",
            license="MIT (upstream repo code); FlyWire/FAFB data terms per upstream repository",
            attribution=(
                "Shiu et al. Nature 2024 (10.1038/s41586-024-07763-9); FlyWire Consortium"
            ),
            is_synthetic_fixture=False,
            credentials_required=False,
            approval_required=True,
            total_estimated_bytes=COMPLETENESS_BYTES + CONNECTIVITY_BYTES,
            files=(
                PlannedFile(
                    name=COMPLETENESS_FILENAME,
                    role="neuron_table",
                    uri=f"{SHIU_BASE_URI}/{COMPLETENESS_FILENAME}",
                    estimated_bytes=COMPLETENESS_BYTES,
                    upstream_checksum=COMPLETENESS_BLOB_SHA1,
                ),
                PlannedFile(
                    name=CONNECTIVITY_FILENAME,
                    role="connectivity_table",
                    uri=f"{SHIU_BASE_URI}/{CONNECTIVITY_FILENAME}",
                    estimated_bytes=CONNECTIVITY_BYTES,
                    upstream_checksum=CONNECTIVITY_BLOB_SHA1,
                ),
            ),
            notes=(
                "Exact FlyWire v630 release used for Shiu et al. (2024) benchmark.",
                "sez_neurons.pickle excluded per AGENTS.md section 13 (no untrusted pickle).",
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
        is_synthetic_fixture: bool = False,
        quarantine_invalid: bool = False,
        require_anchors: bool = True,
    ) -> Path:
        """Normalize FlyWire v630 raw CSV + Parquet into canonical Parquet tables and manifest."""
        comp_path = raw_dir / COMPLETENESS_FILENAME
        conn_path = raw_dir / CONNECTIVITY_FILENAME
        for req in (comp_path, conn_path):
            if not req.is_file():
                raise DataGateError(f"Missing required raw FlyWire v630 file: {req}")

        out_dir.mkdir(parents=True, exist_ok=True)
        curated_dir = out_dir / "curated"
        curated_dir.mkdir(parents=True, exist_ok=True)

        # 1. Completeness table (empty first header column is neuron ID)
        df_comp_raw = pl.read_csv(
            comp_path,
            has_header=True,
            new_columns=["source_neuron_id", "completed"],
            schema_overrides={"source_neuron_id": pl.String, "completed": pl.Boolean},
        ).with_row_index("source_index", offset=0)

        comp_invalid_mask = (
            pl.col("source_neuron_id").is_null()
            | (pl.col("source_neuron_id").str.len_chars() == 0)
            | pl.col("source_neuron_id").is_duplicated()
        )
        invalid_comp = df_comp_raw.filter(comp_invalid_mask)
        valid_comp = df_comp_raw.filter(~comp_invalid_mask)

        # 2. Connectivity table + index-to-ID reconciliation
        df_con_raw = pl.read_parquet(conn_path).with_row_index("raw_row_index", offset=0)
        required_cols = {
            "Presynaptic_ID",
            "Postsynaptic_ID",
            "Presynaptic_Index",
            "Postsynaptic_Index",
            "Connectivity",
            "Excitatory",
            "Excitatory x Connectivity",
        }
        missing_cols = sorted(required_cols - set(df_con_raw.columns))
        if missing_cols:
            raise DataGateError(f"FlyWire v630 connectivity missing columns: {missing_cols}")

        idx_lookup = valid_comp.select(
            pl.col("source_index").cast(pl.Int64),
            pl.col("source_neuron_id"),
        )
        df_con_typed = (
            df_con_raw.with_columns(
                pl.col("Presynaptic_ID").cast(pl.String).alias("pre_source_id"),
                pl.col("Postsynaptic_ID").cast(pl.String).alias("post_source_id"),
                pl.col("Presynaptic_Index").cast(pl.Int64),
                pl.col("Postsynaptic_Index").cast(pl.Int64),
                pl.col("Connectivity").cast(pl.Int64),
                pl.col("Excitatory").cast(pl.Int64),
                pl.col("Excitatory x Connectivity").cast(pl.Int64),
            )
            .join(
                idx_lookup.select(
                    pl.col("source_index").alias("Presynaptic_Index"),
                    pl.col("source_neuron_id").alias("expected_pre_id"),
                ),
                on="Presynaptic_Index",
                how="left",
            )
            .join(
                idx_lookup.select(
                    pl.col("source_index").alias("Postsynaptic_Index"),
                    pl.col("source_neuron_id").alias("expected_post_id"),
                ),
                on="Postsynaptic_Index",
                how="left",
            )
        )

        con_invalid_expr = (
            pl.col("pre_source_id").is_null()
            | pl.col("post_source_id").is_null()
            | pl.col("expected_pre_id").is_null()
            | (pl.col("expected_pre_id") != pl.col("pre_source_id"))
            | pl.col("expected_post_id").is_null()
            | (pl.col("expected_post_id") != pl.col("post_source_id"))
            | pl.col("Connectivity").is_null()
            | (pl.col("Connectivity") <= 0)
            | pl.col("Excitatory").is_null()
            | (~pl.col("Excitatory").is_in([-1, 0, 1]))
            | pl.col("Excitatory x Connectivity").is_null()
            | (
                (pl.col("Excitatory") * pl.col("Connectivity"))
                != pl.col("Excitatory x Connectivity")
            )
        )
        invalid_conns = df_con_typed.filter(con_invalid_expr)
        valid_conns = df_con_typed.filter(~con_invalid_expr)

        # Build quarantine table cleanly (zero heavy serialization when valid)
        q_frames: list[pl.DataFrame] = []
        if invalid_comp.height > 0:
            q_frames.append(
                invalid_comp.select(
                    pl.lit("neurons").alias("table"),
                    pl.col("source_index").cast(pl.Int64).alias("raw_row_index"),
                    pl.lit("invalid_or_duplicate_neuron_id").alias("reason"),
                    pl.struct(["source_neuron_id", "completed"])
                    .struct.json_encode()
                    .alias("raw_record"),
                )
            )
        if invalid_conns.height > 0:
            q_frames.append(
                invalid_conns.select(
                    pl.lit("connections").alias("table"),
                    pl.col("raw_row_index").cast(pl.Int64),
                    pl.lit("fk_index_sign_or_count_mismatch").alias("reason"),
                    pl.struct(
                        [
                            "pre_source_id",
                            "post_source_id",
                            "Presynaptic_Index",
                            "Postsynaptic_Index",
                            "Connectivity",
                            "Excitatory",
                        ]
                    )
                    .struct.json_encode()
                    .alias("raw_record"),
                )
            )
        if q_frames:
            q_df = pl.concat(q_frames)
            q_path = out_dir / "quarantine.parquet"
            q_df.write_parquet(q_path)
            n_quarantined = q_df.height
            if not quarantine_invalid:
                raise DataGateError(
                    f"FlyWire v630 ingest quarantined {n_quarantined} invalid record(s) into "
                    f"{q_path}; failing closed because quarantine_invalid=False"
                )
        else:
            q_path = _write_empty_quarantine(out_dir)
            n_quarantined = 0

        # 3. Canonical neurons table
        ann_status = (
            "synthetic_fixture" if is_synthetic_fixture else "flywire_v630_completeness_table"
        )
        neurons_out = valid_comp.select(
            pl.lit(self.dataset_id).alias("dataset_id"),
            pl.lit("v630").alias("release"),
            pl.lit("flywire_fafb_female_01").alias("specimen_id"),
            pl.col("source_neuron_id"),
            pl.col("source_index").cast(pl.Int64),
            pl.col("completed").fill_null(False).alias("completed"),
            pl.lit(ann_status).alias("annotation_status"),
            pl.lit(f"github:philshiu/Drosophila_brain_model@{SHIU_COMMIT}").alias("provenance"),
        )

        # 4. Canonical connections table (preserve self-loops/reciprocals; sum exact duplicates)
        raw_valid_edge_count = valid_conns.height
        grouped_conns = valid_conns.group_by(
            ["pre_source_id", "post_source_id"], maintain_order=False
        ).agg(pl.col("Connectivity").sum().cast(pl.Int64).alias("synapse_count"))
        duplicate_pairs_collapsed = raw_valid_edge_count - grouped_conns.height

        conns_out = grouped_conns.select(
            pl.lit(self.dataset_id).alias("dataset_id"),
            pl.lit("v630").alias("release"),
            pl.lit("flywire_fafb_female_01").alias("specimen_id"),
            pl.col("pre_source_id"),
            pl.col("post_source_id"),
            pl.col("synapse_count"),
            pl.lit(None, dtype=pl.String).alias("region"),
            pl.lit(None, dtype=pl.Float64).alias("confidence"),
            pl.lit("sum").alias("aggregation_policy"),
        )

        # 5. Neurotransmitter sign-only table derived from upstream Excitatory column
        sign_stats = valid_conns.group_by("pre_source_id").agg(
            pl.col("Excitatory").min().alias("min_sign"),
            pl.col("Excitatory").max().alias("max_sign"),
        )
        nts_out = (
            neurons_out.select("source_neuron_id")
            .join(sign_stats, left_on="source_neuron_id", right_on="pre_source_id", how="left")
            .with_columns(
                pl.when(pl.col("min_sign").is_null())
                .then(pl.lit("UNKNOWN"))
                .when(pl.col("min_sign") != pl.col("max_sign"))
                .then(pl.lit("CONFLICTING_SIGN"))
                .when(pl.col("min_sign") == 1)
                .then(pl.lit("EXCITATORY_SIGN"))
                .when(pl.col("min_sign") == -1)
                .then(pl.lit("INHIBITORY_SIGN"))
                .otherwise(pl.lit("UNKNOWN"))
                .alias("neurotransmitter"),
                pl.when(pl.col("min_sign").is_null())
                .then(pl.lit("no_outgoing_edges_for_sign"))
                .when(pl.col("min_sign") != pl.col("max_sign"))
                .then(pl.lit("conflicting_outgoing_signs"))
                .when(pl.col("min_sign") == 0)
                .then(pl.lit("zero_sign_in_upstream_column"))
                .otherwise(pl.lit("sign_only_from_upstream_excitatory_flag"))
                .alias("missingness"),
            )
            .select(
                pl.lit(self.dataset_id).alias("dataset_id"),
                pl.lit("v630").alias("release"),
                pl.lit("flywire_fafb_female_01").alias("specimen_id"),
                pl.col("source_neuron_id"),
                pl.col("neurotransmitter"),
                pl.lit("shiu2024_flywire_v630_excitatory_column").alias("prediction_method"),
                pl.lit(None, dtype=pl.Float64).alias("confidence"),
                pl.col("missingness"),
            )
        )

        # 6. Anchor verification (21 Sugar GRNs + MN9)
        anchor_ids = [*SHIU2024_SUGAR_GRN_IDS, SHIU2024_MN9_ID]
        present_anchors = set(
            neurons_out.filter(pl.col("source_neuron_id").is_in(anchor_ids))[
                "source_neuron_id"
            ].to_list()
        )
        missing_anchors = [aid for aid in anchor_ids if aid not in present_anchors]
        if require_anchors and missing_anchors:
            raise DataGateError(
                f"FlyWire v630 missing {len(missing_anchors)} expected anchor neuron(s): "
                f"{missing_anchors[:5]}"
            )

        # 7. Structural QC summary metrics
        self_loops = int(
            conns_out.filter(pl.col("pre_source_id") == pl.col("post_source_id")).height
        )
        non_self = conns_out.filter(pl.col("pre_source_id") != pl.col("post_source_id")).select(
            "pre_source_id", "post_source_id"
        )
        reciprocal_directed_edges = int(
            non_self.join(
                non_self.select(
                    pl.col("pre_source_id").alias("post_source_id"),
                    pl.col("post_source_id").alias("pre_source_id"),
                ),
                on=["pre_source_id", "post_source_id"],
                how="semi",
            ).height
        )
        nt_counts = {
            row["neurotransmitter"]: int(row["len"])
            for row in nts_out.group_by("neurotransmitter").len().iter_rows(named=True)
        }
        completed_count = int(neurons_out.filter(pl.col("completed")).height)
        total_synapses = int(conns_out["synapse_count"].sum()) if conns_out.height > 0 else 0

        neurons_pq = curated_dir / "neurons.parquet"
        conns_pq = curated_dir / "connections.parquet"
        nts_pq = curated_dir / "neurotransmitters.parquet"
        qc_path = out_dir / "qc_summary.json"

        neurons_out.write_parquet(neurons_pq)
        conns_out.write_parquet(conns_pq)
        nts_out.write_parquet(nts_pq)

        qc_summary = {
            "dataset_id": self.dataset_id,
            "release": "v630",
            "is_synthetic_fixture": is_synthetic_fixture,
            "raw_neuron_rows": df_comp_raw.height,
            "canonical_neuron_count": neurons_out.height,
            "completed_neuron_count": completed_count,
            "incomplete_neuron_count": neurons_out.height - completed_count,
            "raw_connection_rows": df_con_raw.height,
            "canonical_connection_count": conns_out.height,
            "duplicate_pairs_collapsed": duplicate_pairs_collapsed,
            "total_synapse_count": total_synapses,
            "self_loop_count": self_loops,
            "reciprocal_directed_edge_count": reciprocal_directed_edges,
            "reciprocal_pair_count": reciprocal_directed_edges // 2,
            "quarantined_rows": n_quarantined,
            "neurotransmitter_sign_breakdown": nt_counts,
            "sugar_grns_present": sum(
                1 for aid in SHIU2024_SUGAR_GRN_IDS if aid in present_anchors
            ),
            "sugar_grns_expected": len(SHIU2024_SUGAR_GRN_IDS),
            "mn9_present": SHIU2024_MN9_ID in present_anchors,
        }
        qc_path.write_text(json.dumps(qc_summary, indent=2, sort_keys=True), encoding="utf-8")

        parent_raw_files = [
            {
                "name": COMPLETENESS_FILENAME,
                "role": "neuron_table",
                "uri": f"{SHIU_BASE_URI}/{COMPLETENESS_FILENAME}",
                "bytes": comp_path.stat().st_size,
                "sha256": sha256_file(comp_path),
                "upstream_checksum": None if is_synthetic_fixture else COMPLETENESS_BLOB_SHA1,
            },
            {
                "name": CONNECTIVITY_FILENAME,
                "role": "connectivity_table",
                "uri": f"{SHIU_BASE_URI}/{CONNECTIVITY_FILENAME}",
                "bytes": conn_path.stat().st_size,
                "sha256": sha256_file(conn_path),
                "upstream_checksum": None if is_synthetic_fixture else CONNECTIVITY_BLOB_SHA1,
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
            "release": "v630",
            "species": "Drosophila melanogaster",
            "life_stage": "adult",
            "sex": "female",
            "specimen_id": "flywire_fafb_female_01",
            "coverage": (
                "Synthetic schema fixture"
                if is_synthetic_fixture
                else "Adult female central brain & optic lobe snapshot (FlyWire v630 / Shiu 2024)"
            ),
            "source_uri": f"https://github.com/philshiu/Drosophila_brain_model/tree/{SHIU_COMMIT}",
            "source_reference": "Shiu et al. Nature 2024 (10.1038/s41586-024-07763-9)",
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "license": "MIT (upstream code); FlyWire/FAFB data terms per upstream repository",
            "attribution": "Shiu et al. (2024); FlyWire Consortium",
            "is_synthetic_fixture": is_synthetic_fixture,
            "files": files_entries,
            "parent_raw_files": parent_raw_files,
            "adapter_version": ADAPTER_VERSION,
            "transforms": [
                {
                    "step": "normalize_completeness_v630",
                    "description": "Cast 64-bit FlyWire IDs to UTF-8 String; preserve row index",
                    "input_rows": df_comp_raw.height,
                    "output_rows": neurons_out.height,
                    "rejected_rows": invalid_comp.height,
                },
                {
                    "step": "normalize_connectivity_v630",
                    "description": (
                        "Verify index-to-ID mapping, Excitatory*Connectivity consistency, "
                        "positive counts, and aggregate duplicate pairs by sum"
                    ),
                    "input_rows": df_con_raw.height,
                    "output_rows": conns_out.height,
                    "rejected_rows": invalid_conns.height,
                },
                {
                    "step": "derive_sign_only_neurotransmitters",
                    "description": (
                        "Record sign-only categories EXCITATORY_SIGN/INHIBITORY_SIGN/"
                        "CONFLICTING_SIGN/UNKNOWN from upstream Excitatory flag without "
                        "fabricating chemical identities"
                    ),
                    "input_rows": neurons_out.height,
                    "output_rows": nts_out.height,
                    "rejected_rows": 0,
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
                    "index_to_id_consistent": invalid_conns.height == 0,
                    "foreign_keys_valid": True,
                    "positive_synapse_counts": True,
                    "anchors_present": len(missing_anchors) == 0,
                },
            },
            "known_limitations": [
                "FlyWire v630 provides binary Excitatory (+1/-1) sign only, not per-transmitter "
                "ACh/GABA/Glu predictions or postsynaptic receptor affinities.",
                "Synapse count is an integer structural count, "
                "not a measured physiological conductance.",
                "Historical v630 release is preserved strictly for Shiu et al. (2024) reproduction "
                "and must not be pooled with v783 or MaleCNS node IDs.",
            ],
            "unknown_field_reasons": {
                "region": "Upstream v630 flat connectivity table omits neuropil region breakdown.",
                "confidence": (
                    "Upstream v630 table provides integer synapse counts "
                    "without per-edge confidence."
                ),
            },
        }

        manifest_path = out_dir / "dataset_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        validate_canonical_dataset(out_dir)
        return manifest_path

    def validate(self, dataset_dir: Path) -> dict[str, Any]:
        return validate_canonical_dataset(dataset_dir)
