"""The rustworkx adapter.

Owns three things and no more: whether the library is installed, what
version it is, and how to turn `GraphData` into a `rx.PyDiGraph` (or
`rx.PyGraph`) whose node indices match `node_ids`.

Algorithm calls live beside the algorithm, in
`algorithms/<id>/implementations/rustworkx.py`, so adding an algorithm
never means editing this file.
"""

from __future__ import annotations

from gigi.adapters.base import ConvertedGraph
from gigi.graph import GraphData

NAME = "rustworkx"


def available() -> bool:
    """Is the library importable in this environment?"""
    try:
        import rustworkx  # noqa: F401
    except ImportError:
        return False
    return True


def version() -> str | None:
    """The installed version, recorded on every run, or None if absent."""
    try:
        import rustworkx
    except ImportError:
        return None
    return getattr(rustworkx, "__version__", None)


def convert(graph: GraphData) -> ConvertedGraph:
    """Build the engine's graph object from Gigi's neutral one."""
    import rustworkx as rx

    node_ids = graph.node_ids
    native = rx.PyDiGraph(multigraph=True) if graph.directed else rx.PyGraph(multigraph=True)
    indices = native.add_nodes_from(node_ids)
    index_of = {node: index for node, index in zip(node_ids, indices)}

    weight_column = graph.weight_column
    for source, target, weight in graph.edge_list():
        payload = weight if weight is not None else 1.0
        native.add_edge(index_of[source], index_of[target], payload)

    # rustworkx keys results by node index; `node_ids` is aligned with the
    # indices returned by add_nodes_from so the harness can map back.
    return ConvertedGraph(
        native=native,
        node_ids=node_ids,
        directed=graph.directed,
        has_weights=weight_column is not None,
    )
