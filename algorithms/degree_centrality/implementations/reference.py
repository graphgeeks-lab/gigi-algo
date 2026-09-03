"""Degree centrality, written to be read.

The simplest centrality there is, which makes it the best place to see what
Gigi is actually doing: one loop over the edges, and three semantic choices
(direction, normalisation, self loops) that the engines make differently.
"""

from __future__ import annotations

# Gigi's canonical defaults. Both are choices, and both are recorded on every
# run rather than assumed.
DEFAULT_NORMALIZED = True
DEFAULT_MODE = "all"


def degree_centrality(nodes, edges, normalized=True, mode="all", directed=True):
    """Each node's degree, optionally divided by the largest degree it could have.

        C(v) = deg(v) / (n - 1)

    `deg(v)` counts edge *incidences*, not neighbours: two parallel edges count
    twice, and a self loop counts twice on a directed graph because it is both
    an out-edge and an in-edge. Both of those are choices; see
    `maths.under_determined` in algorithm.yaml.

    On a directed graph `mode` selects which incidences count:

        all   in-degree plus out-degree
        in    edges arriving
        out   edges leaving

    On an undirected graph every edge is traversable both ways, so `mode` does
    not apply and every incidence counts.

    `edges` is a list of (source, target, weight) triples. Weights are ignored:
    degree centrality counts connections, not their strength.
    """
    degree = {node: 0 for node in nodes}

    for source, target, _weight in edges:
        if not directed or mode in ("all", "out"):
            degree[source] += 1
        if not directed or mode in ("all", "in"):
            degree[target] += 1

    if not normalized or len(nodes) < 2:
        return degree

    # A node cannot be adjacent to more than n - 1 others, so this puts scores
    # on a scale that is comparable across graphs of different sizes.
    scale = len(nodes) - 1
    return {node: value / scale for node, value in degree.items()}


def run(graph, params):
    """Gigi entry point: (ConvertedGraph, canonical params) -> (scores, effective)."""
    normalized = _or(params.get("normalized"), DEFAULT_NORMALIZED)
    mode = _or(params.get("mode"), DEFAULT_MODE)

    scores = degree_centrality(
        graph.native["nodes"],
        graph.native["edges"],
        normalized=normalized,
        mode=mode,
        directed=graph.directed,
    )

    effective = {
        "normalized": normalized,
        "mode": mode if graph.directed else "all (undirected: mode does not apply)",
        "directed": graph.directed,
        "counts": "edge incidences, so parallel edges and self loops count twice",
        "weights": "ignored",
    }
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
