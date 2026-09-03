"""Readable reference implementation — a working example.

This template implements degree centrality. Replace it with your algorithm and
keep the shape: the algorithm in a plain function, `run` as a thin entry point.

Rules:
  - no engine libraries;
  - one line of code per line of maths where you can manage it;
  - correctness and clarity over speed. This is the oracle and the teaching
    artifact, never a benchmark target.
"""

from __future__ import annotations


def degree_centrality(nodes, edges, normalized=True, directed=True):
    """Each node's degree, optionally divided by (n - 1).

        C(v) = deg(v) / (n - 1)

    On a directed graph `deg(v)` here means in-degree plus out-degree, which is
    a choice: in-degree alone and out-degree alone are equally defensible
    readings of "degree centrality", and engines do not all agree. Choices like
    this one are exactly what belongs in `maths.md` and, when engines differ
    over them, in `divergences`.

    `edges` is a list of (source, target, weight) triples, where weight is None
    when the dataset is unweighted.
    """
    degree = {node: 0 for node in nodes}
    for source, target, _weight in edges:
        degree[source] += 1
        degree[target] += 1

    if not normalized or len(nodes) < 2:
        return degree

    scale = len(nodes) - 1
    return {node: value / scale for node, value in degree.items()}


def run(graph, params):
    """Gigi entry point.

    graph  -- a ConvertedGraph. For the reference engine, `graph.native` is
              {"nodes": [...], "edges": [(source, target, weight), ...]}.
    params -- canonical parameters, as named in algorithm.yaml.

    Returns (result, effective_parameters).

    `result` for a node_score algorithm may be a dict keyed by node id, a dict
    keyed by node index, or a sequence aligned with `graph.node_ids` -- Gigi
    normalises all three.

    `effective_parameters` must record what was *actually* used, including any
    value the engine chose for you. That record is the whole point: an engine
    default nobody wrote down is an engine default nobody can audit.
    """
    normalized = params.get("normalized")
    normalized = True if normalized is None else bool(normalized)

    scores = degree_centrality(
        graph.native["nodes"],
        graph.native["edges"],
        normalized=normalized,
        directed=graph.directed,
    )

    effective = {
        "normalized": normalized,
        "degree": "in + out",
        "directed": graph.directed,
    }
    return scores, effective
