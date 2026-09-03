"""Engine implementation — a working example.

This file calls the engine. It never reimplements it: if you find yourself
writing a loop over nodes here, the code belongs in reference.py instead.

Conversion from Gigi's neutral GraphData to the engine's graph object has
already happened in gigi/adapters/networkx.py, so `graph.native` is an
nx.MultiDiGraph (or nx.MultiGraph for an undirected dataset) keyed by canonical
node id.
"""

from __future__ import annotations

# Write the engine's own defaults down as constants. They are the values most
# likely to differ from another engine's, and the ones least likely to be
# noticed. nx.degree_centrality takes no options at all: it always normalises,
# and on a directed graph it always uses total degree.
ENGINE_ALWAYS_NORMALIZES = True
ENGINE_DEGREE = "in + out"


def run(graph, params):
    import networkx as nx

    requested_normalized = params.get("normalized")
    requested_normalized = True if requested_normalized is None else bool(requested_normalized)

    scores = nx.degree_centrality(graph.native)

    if not requested_normalized:
        # The engine gives us no way to turn normalisation off, so undo it and
        # say so rather than silently returning the wrong thing.
        scale = max(len(graph.node_ids) - 1, 1)
        scores = {node: value * scale for node, value in scores.items()}

    effective = {
        "normalized": requested_normalized,
        "engine_normalizes": ENGINE_ALWAYS_NORMALIZES,
        "degree": ENGINE_DEGREE,
        "rescaled_by_gigi": not requested_normalized,
    }
    return scores, effective
