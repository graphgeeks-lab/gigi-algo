"""Fixtures must be exactly what graph.yaml says they are."""

from __future__ import annotations

import pytest

from gigi.graph import DatasetError, list_datasets, load_graph, profile_graph

DATASETS = list_datasets()


def test_datasets_exist():
    assert DATASETS


@pytest.mark.parametrize("dataset_id", DATASETS)
def test_counts_match_metadata(dataset_id):
    # load_graph raises if the counts disagree; this asserts the check ran.
    graph = load_graph(dataset_id)
    profile = profile_graph(graph)
    assert profile.node_count == graph.metadata.expected["nodes"]
    assert profile.edge_count == graph.metadata.expected["edges"]


@pytest.mark.parametrize("dataset_id", DATASETS)
def test_declared_features_are_true(dataset_id):
    graph = load_graph(dataset_id)
    profile = profile_graph(graph)
    features = graph.metadata.features

    assert profile.weighted == features.get("weighted", False)
    assert (profile.self_loop_count > 0) == features.get("self_loops", False)
    assert (profile.duplicate_edge_count > 0) == features.get("duplicate_edges", False)
    if graph.directed:
        assert (profile.dangling_node_count > 0) == features.get("dangling_nodes", False)


def test_null_endpoints_are_rejected(tmp_path):
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "edges.csv").write_text("source,target\na,b\n,c\n", encoding="utf-8")
    (directory / "graph.yaml").write_text(
        "id: broken\ndirected: true\nedges: {source: source, target: target}\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetError, match="null source/target"):
        load_graph(directory)


def test_nodes_are_inferred_when_no_node_table(tmp_path):
    directory = tmp_path / "inferred"
    directory.mkdir()
    (directory / "edges.csv").write_text("source,target\na,b\nb,c\n", encoding="utf-8")
    (directory / "graph.yaml").write_text(
        "id: inferred\ndirected: true\nedges: {source: source, target: target}\n",
        encoding="utf-8",
    )
    assert load_graph(directory).node_ids == ["a", "b", "c"]


def test_isolated_nodes_need_a_node_table():
    """disconnected-small exists to prove this: n6 has no edges, so it only
    exists because nodes.csv declares it."""
    graph = load_graph("disconnected-small")
    assert "n6" in graph.node_ids
