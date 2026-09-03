"""The reference implementation is the oracle, so it gets checked against
closed-form answers rather than against another engine.

This is the one place a per-algorithm test file is worth writing by hand: the
conformance suite can prove the engines agree with the reference, but only
mathematics can prove the reference is right.
"""

from __future__ import annotations

import pytest

from gigi import registry


@pytest.fixture(scope="module")
def pagerank():
    return registry.load_implementation("pagerank", "reference").pagerank


def test_symmetric_cycle_is_uniform(pagerank):
    """Every node in a directed cycle is interchangeable, so every score is 1/n."""
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b", None), ("b", "c", None), ("c", "d", None), ("d", "a", None)]
    scores, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False)
    for value in scores.values():
        assert value == pytest.approx(0.25)


def test_scores_sum_to_one(pagerank):
    nodes = ["a", "b", "c", "d", "e"]
    edges = [("a", "b", None), ("b", "c", None), ("c", "a", None), ("d", "e", None)]
    scores, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False)
    assert sum(scores.values()) == pytest.approx(1.0)


def test_dangling_node_mass_is_conserved(pagerank):
    """A sink absorbs rank every iteration; conservation only holds because the
    absorbed mass is explicitly redistributed."""
    nodes = ["a", "b"]
    edges = [("a", "b", None)]
    scores, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False)
    assert sum(scores.values()) == pytest.approx(1.0)
    assert scores["b"] > scores["a"]


def test_two_node_cycle_has_closed_form(pagerank):
    """a <-> b with damping d: both nodes are symmetric, so both are 1/2."""
    nodes = ["a", "b"]
    edges = [("a", "b", None), ("b", "a", None)]
    scores, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False)
    assert scores["a"] == pytest.approx(0.5)
    assert scores["b"] == pytest.approx(0.5)


def test_weights_change_the_ranking(pagerank):
    nodes = ["a", "b", "c"]
    edges = [("a", "b", 1.0), ("a", "c", 99.0)]
    unweighted, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False)
    weighted, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=True)
    assert unweighted["b"] == pytest.approx(unweighted["c"])
    assert weighted["c"] > weighted["b"]


def test_undirected_edges_travel_both_ways(pagerank):
    nodes = ["a", "b"]
    edges = [("a", "b", None)]
    scores, _ = pagerank(nodes, edges, 0.85, 1e-12, 500, weighted=False, directed=False)
    assert scores["a"] == pytest.approx(0.5)
    assert scores["b"] == pytest.approx(0.5)


def test_empty_graph(pagerank):
    scores, iterations = pagerank([], [], 0.85, 1e-12, 500, weighted=False)
    assert scores == {}
    assert iterations == 0
