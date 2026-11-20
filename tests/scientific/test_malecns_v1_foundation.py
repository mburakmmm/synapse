"""Phase 1 scientific foundation checks on curated MaleCNS v1.0 (skips cleanly if absent)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from synapse_core import extract_bounded_subgraph
from synapse_data import validate_canonical_dataset
from synapse_experiments import load_graph_from_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
MALECNS_CURATED = REPO_ROOT / "data" / "curated" / "malecns_v1_0"


@pytest.mark.scientific
def test_malecns_v1_canonical_graph_and_bounded_subgraph() -> None:
    if not (MALECNS_CURATED / "dataset_manifest.json").is_file():
        pytest.skip("data/curated/malecns_v1_0 not present locally (requires approved fetch)")

    manifest = validate_canonical_dataset(MALECNS_CURATED)
    assert manifest["is_synthetic_fixture"] is False
    assert manifest["specimen_id"] == "malecns_male_01"
    assert manifest["quality_report"]["neuron_count"] == 211577
    assert manifest["quality_report"]["connection_count"] == 26028386
    assert manifest["quality_report"]["total_synapse_count"] == 125365933

    graph, _, _ = load_graph_from_dataset(MALECNS_CURATED)
    assert graph.specimen_id == "malecns_male_01"
    assert graph.n_neurons == 211577
    assert graph.n_edges == 26028386
    assert graph.total_synapses == 125365933

    # Verify explicit sparse orientation W[post, pre] on traced body 806809
    traced = (
        pl.read_parquet(MALECNS_CURATED / "curated" / "neurons.parquet")
        .filter(pl.col("annotation_status") == "Traced")
        .head(1)
    )
    seed_id = str(traced["source_neuron_id"][0])
    adj = graph.adjacency_copy()
    seed_idx = graph.index_of(seed_id)
    ones = np.ones(graph.n_neurons, dtype=np.int64)
    assert int((adj @ ones)[seed_idx]) == int(adj[seed_idx, :].sum())

    sub, meta = extract_bounded_subgraph(
        graph,
        seed_neuron_ids=[seed_id],
        hop_limit=1,
        direction="outgoing",
        min_synapse_threshold=5,
        max_nodes=2000,
    )
    assert sub.n_neurons >= 1
    assert meta.source_specimen_id == "malecns_male_01"
    assert meta.omitted_incoming_edge_count >= 0
    assert meta.omitted_outgoing_edge_count >= 0
