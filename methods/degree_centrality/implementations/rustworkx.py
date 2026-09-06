"""Degree centrality via rustworkx.

Like NetworkX, rustworkx splits the directed modes across three functions and
always normalises.

Note: on graphs with parallel edges or self loops, `rx.degree_centrality`
returns values that differ from in-degree plus out-degree. That is recorded as
a divergence in method.yaml and reproduced by CI; this file does nothing to
work around it, because an adapter's job is to report what the backend did.
"""

from __future__ import annotations

ENGINE_ALWAYS_NORMALIZES = True


def run(graph, params):
    import rustworkx as rx

    normalized = _or(params.get("normalized"), True)
    mode = _or(params.get("mode"), "all")

    functions = {
        "all": rx.degree_centrality,
        "in": rx.in_degree_centrality,
        "out": rx.out_degree_centrality,
    }
    # The directional variants need a PyDiGraph, and on an undirected graph the
    # distinction does not exist.
    applied = mode if graph.directed else "all"
    scores = dict(functions[applied](graph.native))

    if not normalized:
        scale = max(len(graph.node_ids) - 1, 1)
        scores = {node: value * scale for node, value in scores.items()}

    effective = {
        "function": f"rx.{functions[applied].__name__}",
        "normalized": normalized,
        "engine_normalizes": ENGINE_ALWAYS_NORMALIZES,
        "rescaled_by_gigi": not normalized,
        "mode": applied,
    }
    # Keyed by node index; Gigi maps it back to node ids.
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
