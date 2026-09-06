"""Fixtures must be exactly what dataset.yaml says they are.

Split by kind, because the claims differ: a graph declares whether it is
weighted and whether it has dangling nodes, a set of vectors declares how many
of them there are and how wide. What does not differ is that the metadata is
checked against the file rather than trusted.
"""

from __future__ import annotations

import pytest

from gigi.data import list_datasets, load_dataset, profile_dataset
from gigi.graph import DatasetError, load_graph, profile_graph
from gigi.vectors import VectorDataError

DATASETS = list_datasets()
GRAPHS = list_datasets("graph")
VECTORS = list_datasets("vectors")


def test_datasets_exist():
    assert DATASETS


def test_both_kinds_are_present():
    """The schema stopped being graph-shaped in PR 1; this is the fixture-level
    proof that the data layer did too."""
    assert GRAPHS and VECTORS


@pytest.mark.parametrize("dataset_id", DATASETS)
def test_a_dataset_loads_by_id_without_being_told_its_kind(dataset_id):
    """One door in. Callers ask for a fixture and get whichever container fits,
    which is what lets the harness be written once."""
    profile = profile_dataset(load_dataset(dataset_id))
    assert profile.kind in {"graph", "vectors"}


# --- graphs -------------------------------------------------------------------


@pytest.mark.parametrize("dataset_id", GRAPHS)
def test_counts_match_metadata(dataset_id):
    # load_graph raises if the counts disagree; this asserts the check ran.
    graph = load_graph(dataset_id)
    profile = profile_graph(graph)
    assert profile.node_count == graph.metadata.expected["nodes"]
    assert profile.edge_count == graph.metadata.expected["edges"]


@pytest.mark.parametrize("dataset_id", GRAPHS)
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
    (directory / "dataset.yaml").write_text(
        "id: broken\ndirected: true\nedges: {source: source, target: target}\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetError, match="null source/target"):
        load_graph(directory)


def test_nodes_are_inferred_when_no_node_table(tmp_path):
    directory = tmp_path / "inferred"
    directory.mkdir()
    (directory / "edges.csv").write_text("source,target\na,b\nb,c\n", encoding="utf-8")
    (directory / "dataset.yaml").write_text(
        "id: inferred\ndirected: true\nedges: {source: source, target: target}\n",
        encoding="utf-8",
    )
    assert load_graph(directory).node_ids == ["a", "b", "c"]


def test_isolated_nodes_need_a_node_table():
    """disconnected-small exists to prove this: n6 has no edges, so it only
    exists because nodes.csv declares it."""
    graph = load_graph("disconnected-small")
    assert "n6" in graph.node_ids


# --- vectors ------------------------------------------------------------------


@pytest.mark.parametrize("dataset_id", VECTORS)
def test_vector_counts_match_metadata(dataset_id):
    data = load_dataset(dataset_id)
    profile = profile_dataset(data)
    assert profile.vector_count == data.metadata.expected["vectors"]
    assert profile.dimensions == data.metadata.expected["dimensions"]


@pytest.mark.parametrize("dataset_id", VECTORS)
def test_declared_vector_features_are_true(dataset_id):
    data = load_dataset(dataset_id)
    profile = profile_dataset(data)
    features = data.metadata.features

    assert (profile.zero_vector_count > 0) == features.get("zero_vectors", False)
    assert profile.has_negative_values == features.get("negative_values", False)


def _vector_fixture(tmp_path, name, csv, extra=""):
    directory = tmp_path / name
    directory.mkdir()
    (directory / "vectors.csv").write_text(csv, encoding="utf-8")
    (directory / "dataset.yaml").write_text(
        f"kind: vectors\nid: {name}\n{extra}", encoding="utf-8"
    )
    return directory


def test_a_vector_id_containing_the_pair_separator_is_rejected(tmp_path):
    """Results are keyed `a|b`. An id containing the separator would make the
    key unparseable, so the loader refuses it rather than letting a result be
    quietly ambiguous."""
    directory = _vector_fixture(tmp_path, "bad-ids", "id,d0\na|b,1\nc,2\n")
    with pytest.raises(VectorDataError, match="pair-key separator"):
        load_dataset(directory)


def test_duplicate_vector_ids_are_rejected(tmp_path):
    directory = _vector_fixture(tmp_path, "dupes", "id,d0\na,1\na,2\n")
    with pytest.raises(VectorDataError, match="duplicate"):
        load_dataset(directory)


def test_a_non_finite_value_is_rejected(tmp_path):
    """No backend should ever be handed a NaN it did not produce itself."""
    directory = _vector_fixture(tmp_path, "nans", "id,d0\na,1\nb,nan\n")
    with pytest.raises(VectorDataError, match="non-finite"):
        load_dataset(directory)


def test_a_wrong_expected_count_is_caught(tmp_path):
    directory = _vector_fixture(
        tmp_path, "miscounted", "id,d0\na,1\nb,2\n", extra="expected:\n  vectors: 3\n"
    )
    with pytest.raises(VectorDataError, match="expects 3 vectors"):
        load_dataset(directory)


def test_metadata_without_a_vectors_file_is_an_error(tmp_path):
    directory = tmp_path / "empty-dir"
    directory.mkdir()
    (directory / "dataset.yaml").write_text("kind: vectors\nid: empty-dir\n", encoding="utf-8")
    with pytest.raises(VectorDataError, match="no vectors.csv"):
        load_dataset(directory)
