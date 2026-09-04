"""The NetworkX adapter.

Owns three things and no more: whether the library is installed, what
version it is, and how to turn `GraphData` into an `nx.MultiDiGraph`
(or `nx.MultiGraph` for an undirected dataset).

Algorithm calls live beside the algorithm, in
`algorithms/<id>/implementations/networkx.py`, so adding an algorithm
never means editing this file.
"""

from __future__ import annotations

from gigi.backends.base import ConvertedGraph, Dataset, require_graph

NAME = "networkx"


def available() -> bool:
    """Is the library importable in this environment?"""
    try:
        import networkx  # noqa: F401
    except ImportError:
        return False
    return True


def version() -> str | None:
    """The installed version, recorded on every run, or None if absent."""
    try:
        import networkx
    except ImportError:
        return None
    return networkx.__version__


def convert(data: Dataset) -> ConvertedGraph:
    """Build the backend's graph object from Gigi's neutral one."""
    graph = require_graph(NAME, data)

    import networkx as nx

    # MultiGraph, because ADR 0003 says duplicate edges are preserved rather
    # than silently collapsed.
    native = nx.MultiDiGraph() if graph.directed else nx.MultiGraph()
    native.add_nodes_from(graph.node_ids)

    weight_column = graph.weight_column
    for source, target, weight in graph.edge_list():
        if weight_column is not None:
            native.add_edge(source, target, weight=weight)
        else:
            native.add_edge(source, target)

    return ConvertedGraph(
        native=native,
        node_ids=list(native.nodes()),
        directed=graph.directed,
        has_weights=weight_column is not None,
        weight_attribute="weight" if weight_column is not None else None,
    )
