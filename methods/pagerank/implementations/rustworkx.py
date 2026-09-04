"""PageRank via rustworkx."""

from __future__ import annotations

# rustworkx takes a callable over the edge payload rather than an attribute
# name, and passing nothing means unweighted.
ENGINE_DEFAULT_WEIGHT_FN = None
ENGINE_DEFAULT_MAX_ITER = 100
ENGINE_DEFAULT_TOL = 1.0e-6


def run(graph, params):
    import rustworkx as rx

    weight_property = params.get("weight_property")
    use_weights = bool(weight_property) and graph.has_weights

    effective = {
        "alpha": _or(params.get("damping"), 0.85),
        "max_iter": _or(params.get("max_iterations"), ENGINE_DEFAULT_MAX_ITER),
        "tol": _or(params.get("tolerance"), ENGINE_DEFAULT_TOL),
        "weight_fn": "float(payload)" if use_weights else None,
        "personalization": None,
        "dangling": None,
    }

    scores = rx.pagerank(
        graph.native,
        alpha=effective["alpha"],
        weight_fn=float if use_weights else ENGINE_DEFAULT_WEIGHT_FN,
        max_iter=effective["max_iter"],
        tol=effective["tol"],
    )
    # A mapping keyed by node index; Gigi maps it back to node ids.
    return dict(scores), effective


def _or(value, fallback):
    return fallback if value is None else value
