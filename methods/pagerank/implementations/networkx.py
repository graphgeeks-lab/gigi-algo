"""PageRank via NetworkX.

Adapters call the backend. They never reimplement it -- if this file ever
contains a loop over nodes, it is in the wrong place.
"""

from __future__ import annotations

# What networkx.pagerank uses when you pass nothing. Recorded rather than
# assumed, because these values are exactly what makes backends disagree.
ENGINE_DEFAULT_WEIGHT = "weight"
ENGINE_DEFAULT_MAX_ITER = 100
ENGINE_DEFAULT_TOL = 1.0e-6


def run(graph, params):
    import networkx as nx

    weight_property = params.get("weight_property")
    if weight_property is None:
        weight = ENGINE_DEFAULT_WEIGHT  # the backend's default, made visible
    elif weight_property is False:
        weight = None
    else:
        # The adapter attached the weights under its own name; the dataset's
        # column name does not exist inside the nx graph.
        weight = graph.weight_attribute

    effective = {
        "alpha": _or(params.get("damping"), 0.85),
        "max_iter": _or(params.get("max_iterations"), ENGINE_DEFAULT_MAX_ITER),
        "tol": _or(params.get("tolerance"), ENGINE_DEFAULT_TOL),
        "weight": weight,
        "personalization": None,
        "dangling": None,
    }

    scores = nx.pagerank(
        graph.native,
        alpha=effective["alpha"],
        max_iter=effective["max_iter"],
        tol=effective["tol"],
        weight=effective["weight"],
    )
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
