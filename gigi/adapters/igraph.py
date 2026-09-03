"""The python-igraph adapter.

Owns three things and no more: whether the library is installed, what
version it is, and how to turn `GraphData` into an `ig.Graph` whose
vertex order matches `node_ids`.

Algorithm calls live beside the algorithm, in
`algorithms/<id>/implementations/igraph.py`, so adding an algorithm
never means editing this file.
"""

from __future__ import annotations

from gigi.adapters.base import ConvertedGraph
from gigi.graph import GraphData

NAME = "igraph"


def available() -> bool:
    """Is the library importable in this environment?"""
    try:
        import igraph  # noqa: F401
    except ImportError:
        return False
    return True


def version() -> str | None:
    """The installed version, recorded on every run, or None if absent."""
    try:
        import igraph
    except ImportError:
        return None
    return igraph.__version__


def convert(graph: GraphData) -> ConvertedGraph:
    """Build the engine's graph object from Gigi's neutral one."""
    import igraph as ig

    node_ids = graph.node_ids
    index_of = {node: i for i, node in enumerate(node_ids)}

    edges = graph.edge_list()
    native = ig.Graph(
        n=len(node_ids),
        edges=[(index_of[s], index_of[t]) for s, t, _ in edges],
        directed=graph.directed,
    )
    native.vs["name"] = node_ids

    weight_column = graph.weight_column
    if weight_column is not None and edges:
        native.es["weight"] = [w if w is not None else 1.0 for _, _, w in edges]

    return ConvertedGraph(
        native=native,
        node_ids=node_ids,
        directed=graph.directed,
        has_weights=weight_column is not None,
    )
