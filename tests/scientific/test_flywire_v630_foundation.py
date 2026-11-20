"""Phase 1 scientific foundation checks on curated FlyWire v630 (skips cleanly if absent)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from synapse_cli.main import main as cli_main
from synapse_core import extract_bounded_subgraph
from synapse_data import SHIU2024_MN9_ID, SHIU2024_SUGAR_GRN_IDS, validate_canonical_dataset
from synapse_experiments import load_graph_from_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
FLYWIRE_V630_CURATED = REPO_ROOT / "data" / "curated" / "flywire_fafb_v630"


@pytest.mark.scientific
def test_flywire_v630_canonical_graph_and_bounded_subgraphs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if not (FLYWIRE_V630_CURATED / "dataset_manifest.json").is_file():
        pytest.skip("data/curated/flywire_fafb_v630 not present locally (requires approved fetch)")

    manifest = validate_canonical_dataset(FLYWIRE_V630_CURATED)
    assert manifest["is_synthetic_fixture"] is False
    assert manifest["quality_report"]["neuron_count"] == 127400
    assert manifest["quality_report"]["connection_count"] == 14687178
    assert manifest["quality_report"]["total_synapse_count"] == 52793639

    graph, _, _ = load_graph_from_dataset(FLYWIRE_V630_CURATED)
    assert graph.n_neurons == 127400
    assert graph.n_edges == 14687178
    assert graph.total_synapses == 52793639

    for sid in (*SHIU2024_SUGAR_GRN_IDS, SHIU2024_MN9_ID):
        idx = graph.index_of(sid)
        assert graph.neuron_ids[idx] == sid

    # Verify explicit sparse orientation W[post, pre] on MN9 incoming drive
    adj = graph.adjacency_copy()
    mn9_idx = graph.index_of(SHIU2024_MN9_ID)
    ones = np.ones(graph.n_neurons, dtype=np.int64)
    in_synapses = int((adj @ ones)[mn9_idx])
    assert in_synapses == int(adj[mn9_idx, :].sum())
    assert in_synapses > 0

    # Extract 1-hop outgoing bounded subgraph from the 21 Shiu sugar GRNs
    sub_1hop, meta_1hop = extract_bounded_subgraph(
        graph,
        seed_neuron_ids=SHIU2024_SUGAR_GRN_IDS,
        hop_limit=1,
        direction="outgoing",
        min_synapse_threshold=5,
        max_nodes=5000,
    )
    assert sub_1hop.n_neurons > len(SHIU2024_SUGAR_GRN_IDS)
    assert meta_1hop.omitted_incoming_edge_count > 0
    assert meta_1hop.omitted_outgoing_edge_count > 0
    assert (
        sub_1hop.n_edges
        + meta_1hop.omitted_incoming_edge_count
        + meta_1hop.omitted_outgoing_edge_count
    ) <= graph.n_edges

    # CLI bounded subgraph export check on 1-hop incoming neighborhood of MN9
    out_json = tmp_path / "mn9_1hop.json"
    rc = cli_main(
        [
            "graph",
            "subgraph",
            "--dataset-dir",
            str(FLYWIRE_V630_CURATED),
            "--seeds",
            SHIU2024_MN9_ID,
            "--hops",
            "1",
            "--direction",
            "incoming",
            "--min-synapses",
            "5",
            "--max-nodes",
            "500",
            "--out",
            str(out_json),
            "--json",
        ]
    )
    assert rc == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["n_selected_neurons"] >= 2
    assert out_json.is_file()
