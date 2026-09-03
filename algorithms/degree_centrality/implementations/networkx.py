"""Degree centrality via NetworkX.

NetworkX splits the three directed modes across three functions and always
normalises. Neither is wrong; both are defaults a caller never typed, so both
are reported in `effective`.
"""

from __future__ import annotations

# nx.degree_centrality takes no options at all: it always divides by (n - 1),
# and on a directed graph it always uses in-degree plus out-degree.
ENGINE_ALWAYS_NORMALIZES = True


def run(graph, params):
    import networkx as nx

    normalized = _or(params.get("normalized"), True)
    mode = _or(params.get("mode"), "all")

    functions = {
        "all": nx.degree_centrality,
        "in": nx.in_degree_centrality,
        "out": nx.out_degree_centrality,
    }
    # in_/out_degree_centrality require a directed graph, and on an undirected
    # one the distinction does not exist.
    applied = mode if graph.directed else "all"
    scores = functions[applied](graph.native)

    if not normalized:
        # The engine gives no way to switch normalisation off, so undo it and
        # say so rather than returning a number the engine did not produce.
        scale = max(len(graph.node_ids) - 1, 1)
        scores = {node: value * scale for node, value in scores.items()}

    effective = {
        "function": f"nx.{functions[applied].__name__}",
        "normalized": normalized,
        "engine_normalizes": ENGINE_ALWAYS_NORMALIZES,
        "rescaled_by_gigi": not normalized,
        "mode": applied,
    }
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
