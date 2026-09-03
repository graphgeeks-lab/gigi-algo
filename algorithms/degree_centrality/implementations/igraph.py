"""Degree centrality via python-igraph.

igraph offers `degree()` and no normalised centrality wrapper, which is the
opposite of NetworkX: here the engine never normalises and Gigi must. Recorded
in `effective` either way, because a scale factor applied by us is not a result
the engine produced.
"""

from __future__ import annotations

# igraph.degree() returns raw counts and includes self loops by default. Its
# mode names happen to match Gigi's canonical ones.
ENGINE_NORMALIZES = False
ENGINE_COUNTS_LOOPS = True


def run(graph, params):
    normalized = _or(params.get("normalized"), True)
    mode = _or(params.get("mode"), "all")
    applied = mode if graph.directed else "all"

    raw = graph.native.degree(mode=applied, loops=ENGINE_COUNTS_LOOPS)

    if normalized and len(graph.node_ids) > 1:
        scale = len(graph.node_ids) - 1
        scores = [value / scale for value in raw]
    else:
        scores = list(raw)

    effective = {
        "function": "ig.Graph.degree",
        "mode": applied,
        "loops": ENGINE_COUNTS_LOOPS,
        "normalized": normalized,
        "engine_normalizes": ENGINE_NORMALIZES,
        "normalized_by_gigi": normalized,
    }
    # A list aligned with vertex order; Gigi maps it back to node ids.
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
