"""PageRank, written to be read.

This is the oracle every backend is compared against, and a teaching artifact
first: no library calls, no vectorisation, one line of code per line of maths.
It is not a benchmark target. See docs/adr/0002-reference-optimises-readability.md.
"""

from __future__ import annotations

# Gigi's canonical defaults for anything the backends do not agree on.
DEFAULT_DAMPING = 0.85
DEFAULT_TOLERANCE = 1e-12  # tighter than any backend, so the oracle is not the noise
DEFAULT_MAX_ITERATIONS = 500


def pagerank(nodes, edges, damping, tolerance, max_iterations, weighted, directed=True):
    """Power iteration on the Google matrix.

        r(v) = (1 - d)/N  +  d * [ dangling_mass/N + sum_{u -> v} r(u) * w(u,v) / W(u) ]

    where W(u) is u's total outgoing weight and dangling_mass is the rank held
    by nodes with no outgoing edges. Redistributing that mass uniformly is a
    choice, not a law -- it is the choice PageRank's authors made, and one of
    the places backends quietly differ.
    """
    n = len(nodes)
    if n == 0:
        return {}, 0

    position = {node: i for i, node in enumerate(nodes)}
    outgoing_weight = [0.0] * n
    incoming = [[] for _ in range(n)]

    for source, target, weight in edges:
        w = float(weight) if (weighted and weight is not None) else 1.0
        i, j = position[source], position[target]
        outgoing_weight[i] += w
        incoming[j].append((i, w))
        if not directed and i != j:
            # An undirected edge is two arcs. Self loops are already counted once.
            outgoing_weight[j] += w
            incoming[i].append((j, w))

    rank = [1.0 / n] * n
    iterations = 0

    for iterations in range(1, max_iterations + 1):
        dangling_mass = sum(rank[i] for i in range(n) if outgoing_weight[i] == 0.0)
        base = (1.0 - damping) / n + damping * dangling_mass / n

        updated = [base] * n
        for j in range(n):
            inflow = sum(rank[i] * w / outgoing_weight[i] for i, w in incoming[j])
            updated[j] += damping * inflow

        change = sum(abs(updated[i] - rank[i]) for i in range(n))
        rank = updated
        if change < tolerance:
            break

    return {node: rank[position[node]] for node in nodes}, iterations


def run(graph, params):
    """Gigi entry point: (ConvertedGraph, canonical params) -> (scores, effective)."""
    damping = _or(params.get("damping"), DEFAULT_DAMPING)
    tolerance = _or(params.get("tolerance"), DEFAULT_TOLERANCE)
    max_iterations = _or(params.get("max_iterations"), DEFAULT_MAX_ITERATIONS)

    # weight_property: None means "backend default", and this backend's default is
    # unweighted. False means explicitly unweighted. A string names the column.
    weight_property = params.get("weight_property")
    weighted = bool(weight_property) and graph.has_weights

    scores, iterations = pagerank(
        graph.native["nodes"],
        graph.native["edges"],
        damping=damping,
        tolerance=tolerance,
        max_iterations=max_iterations,
        weighted=weighted,
        directed=graph.directed,
    )

    effective = {
        "damping": damping,
        "tolerance": tolerance,
        "max_iterations": max_iterations,
        "weighted": weighted,
        "directed": graph.directed,
        "dangling_mass": "redistributed uniformly",
        "iterations_used": iterations,
    }
    return scores, effective


def _or(value, fallback):
    return fallback if value is None else value
