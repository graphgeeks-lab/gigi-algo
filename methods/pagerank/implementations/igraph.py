"""PageRank via python-igraph."""

from __future__ import annotations

# igraph's default solver is PRPACK, which solves the system directly instead
# of iterating to a tolerance. There is no `tol` or `max_iter` to report.
ENGINE_DEFAULT_WEIGHTS = None  # i.e. unweighted, even when a weight attribute exists
ENGINE_DEFAULT_IMPLEMENTATION = "prpack"


def run(graph, params):
    weight_property = params.get("weight_property")
    if weight_property is None:
        weights = ENGINE_DEFAULT_WEIGHTS
    elif weight_property is False:
        weights = None
    else:
        # Likewise: igraph knows the edge attribute the adapter created, not
        # whatever the CSV column was called.
        weights = graph.weight_attribute if graph.has_weights else None

    effective = {
        "damping": _or(params.get("damping"), 0.85),
        "weights": weights,
        "directed": graph.directed,
        "implementation": ENGINE_DEFAULT_IMPLEMENTATION,
    }

    scores = graph.native.pagerank(
        damping=effective["damping"],
        weights=effective["weights"],
        directed=effective["directed"],
        implementation=effective["implementation"],
    )
    # A list positionally aligned with vertex order; Gigi maps it back to node ids.
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
