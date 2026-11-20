"""Offline schema-exact unit tests for FlyWireV630Adapter and MaleCNSV1Adapter."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from synapse_core import DEFAULT_SIGN_MAP, DirectedConnectomeGraph
from synapse_data import ApprovalRequiredError, DataGateError, FlyWireV630Adapter, MaleCNSV1Adapter
from synapse_experiments import load_graph_from_dataset


def _write_synthetic_v630_raw(raw_dir: Path, *, inject_bad_edge: bool = False) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    # 64-bit FlyWire-scale integer IDs (> 2**53)
    ids = ["720575940624963786", "720575940630233916", "720575940660219265", "720575940699999999"]
    csv_lines = [",Completed", *[f"{nid},True" for nid in ids]]
    (raw_dir / "2023_03_23_completeness_630_final.csv").write_text(
        "\n".join(csv_lines) + "\n", encoding="utf-8"
    )

    rows = [
        {
            "Presynaptic_ID": int(ids[0]),
            "Postsynaptic_ID": int(ids[2]),
            "Presynaptic_Index": 0,
            "Postsynaptic_Index": 2,
            "Connectivity": 15,
            "Excitatory": 1,
            "Excitatory x Connectivity": 15,
        },
        {
            # Node 1 sends both +1 and -1 -> CONFLICTING_SIGN (never silently excitatory)
            "Presynaptic_ID": int(ids[1]),
            "Postsynaptic_ID": int(ids[2]),
            "Presynaptic_Index": 1,
            "Postsynaptic_Index": 2,
            "Connectivity": 10,
            "Excitatory": -1,
            "Excitatory x Connectivity": -10,
        },
        {
            "Presynaptic_ID": int(ids[1]),
            "Postsynaptic_ID": int(ids[3]),
            "Presynaptic_Index": 1,
            "Postsynaptic_Index": 3,
            "Connectivity": 8,
            "Excitatory": 1,
            "Excitatory x Connectivity": 8,
        },
        {
            "Presynaptic_ID": int(ids[2]),
            "Postsynaptic_ID": int(ids[3]),
            "Presynaptic_Index": 2,
            "Postsynaptic_Index": 3,
            "Connectivity": 12,
            "Excitatory": -1,
            "Excitatory x Connectivity": -12,
        },
    ]
    if inject_bad_edge:
        rows.append(
            {
                "Presynaptic_ID": int(ids[0]),
                "Postsynaptic_ID": int(ids[1]),
                "Presynaptic_Index": 999,  # index mismatch -> quarantine
                "Postsynaptic_Index": 1,
                "Connectivity": 5,
                "Excitatory": 1,
                "Excitatory x Connectivity": 5,
            }
        )
    pl.DataFrame(rows).write_parquet(raw_dir / "2023_03_23_connectivity_630_final.parquet")


@pytest.mark.unit
def test_flywire_v630_adapter_normalize_signs_and_quarantine(tmp_path: Path) -> None:
    adapter = FlyWireV630Adapter()
    with pytest.raises(ApprovalRequiredError):
        adapter.fetch(tmp_path / "raw_blocked", approved=False)

    raw_dir = tmp_path / "raw_v630"
    curated_dir = tmp_path / "curated_v630"
    _write_synthetic_v630_raw(raw_dir, inject_bad_edge=False)

    manifest_path = adapter.normalize(
        raw_dir, curated_dir, is_synthetic_fixture=True, require_anchors=False
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["quality_report"]["neuron_count"] == 4
    assert manifest["quality_report"]["connection_count"] == 4
    assert manifest["quality_report"]["total_synapse_count"] == 45

    nts_df = pl.read_parquet(curated_dir / "curated" / "neurotransmitters.parquet")
    nt_by_id = dict(
        zip(nts_df["source_neuron_id"].to_list(), nts_df["neurotransmitter"].to_list(), strict=True)
    )
    assert nt_by_id["720575940624963786"] == "EXCITATORY_SIGN"
    assert nt_by_id["720575940660219265"] == "INHIBITORY_SIGN"
    assert nt_by_id["720575940630233916"] == "CONFLICTING_SIGN"
    assert nt_by_id["720575940699999999"] == "UNKNOWN"
    assert "CONFLICTING_SIGN" not in DEFAULT_SIGN_MAP

    graph, _, _ = load_graph_from_dataset(curated_dir)
    assert isinstance(graph, DirectedConnectomeGraph)
    w = graph.signed_weight_matrix(0.000275, unknown_nt_policy="zero_effect")
    # CONFLICTING_SIGN outgoing edges must map to 0.0 under zero_effect (not +1!)
    idx_conf = graph.index_of("720575940630233916")
    idx_mn9 = graph.index_of("720575940660219265")
    assert w[idx_mn9, idx_conf] == 0.0

    # Corrupt index-to-ID row must quarantine and fail closed
    bad_raw = tmp_path / "raw_v630_bad"
    bad_curated = tmp_path / "curated_v630_bad"
    _write_synthetic_v630_raw(bad_raw, inject_bad_edge=True)
    with pytest.raises(DataGateError, match="quarantined 1 invalid record"):
        adapter.normalize(bad_raw, bad_curated, is_synthetic_fixture=True, require_anchors=False)
    assert pl.read_parquet(bad_curated / "quarantine.parquet").height == 1


@pytest.mark.unit
def test_malecns_v1_adapter_schema_exact_feather_offline(tmp_path: Path) -> None:
    adapter = MaleCNSV1Adapter()
    plan = adapter.plan()
    assert plan.total_estimated_bytes == 14483314 + 43282834 + 1051241946
    with pytest.raises(ApprovalRequiredError):
        adapter.fetch(tmp_path / "mc_blocked", approved=False)

    raw_dir = tmp_path / "mc_raw"
    curated_dir = tmp_path / "mc_curated"
    raw_dir.mkdir(parents=True)

    pl.DataFrame(
        {
            "bodyId": [10001, 10002],
            "type": ["ORN_DM1", "PN_DM1"],
            "superclass": ["sensory", "central"],
            "class": ["olfactory", "projection"],
            "subclass": ["ORN", "uPN"],
            "somaSide": ["L", "L"],
            "status": ["Traced", "Traced"],
        }
    ).write_ipc(raw_dir / "body-annotations-male-cns-v1.0-minconf-0.5.feather")

    pl.DataFrame(
        {
            "body": [10001, 10002],
            "consensus_nt": ["acetylcholine", None],
            "predicted_nt": ["acetylcholine", "histamine"],
            "predicted_nt_confidence": [0.95, 0.88],
            "ground_truth": [None, None],
        }
    ).write_ipc(raw_dir / "body-neurotransmitters-male-cns-v1.0.feather")

    # Body 10003 is unannotated: excluded under annotated_bodies, retained under all_segments
    pl.DataFrame(
        {
            "body_pre": [10001, 10002],
            "body_post": [10002, 10003],
            "weight": [22, 14],
        }
    ).write_ipc(raw_dir / "connectome-weights-male-cns-v1.0-minconf-0.5.feather")

    manifest_path = adapter.normalize(raw_dir, curated_dir, is_synthetic_fixture=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["specimen_id"] == "malecns_male_01"
    assert manifest["quality_report"]["neuron_count"] == 2
    assert manifest["quality_report"]["connection_count"] == 1
    assert manifest["quality_report"]["total_synapse_count"] == 22

    qc_summary = json.loads((curated_dir / "qc_summary.json").read_text(encoding="utf-8"))
    assert qc_summary["excluded_unannotated_fragment_edges"] == 1
    assert qc_summary["excluded_unannotated_fragment_synapses"] == 14

    nts_df = pl.read_parquet(curated_dir / "curated" / "neurotransmitters.parquet")
    nt_map = dict(
        zip(
            nts_df["source_neuron_id"].to_list(),
            nts_df["neurotransmitter"].to_list(),
            strict=True,
        )
    )
    assert nt_map == {"10001": "ACH", "10002": "HIST"}

    all_seg_dir = tmp_path / "mc_curated_all"
    all_manifest_path = adapter.normalize(
        raw_dir, all_seg_dir, scope="all_segments", is_synthetic_fixture=True
    )
    all_manifest = json.loads(all_manifest_path.read_text(encoding="utf-8"))
    assert all_manifest["quality_report"]["neuron_count"] == 3
    assert all_manifest["quality_report"]["connection_count"] == 2
    assert all_manifest["quality_report"]["total_synapse_count"] == 36
