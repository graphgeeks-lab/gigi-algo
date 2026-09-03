"""The reference engine: no third-party library, always available.

Reference implementations are the oracle every other engine is compared
against, and they are teaching artifacts first. They optimise for reading, not
for speed. See ADR 0002.
"""

from __future__ import annotations

from gigi.adapters.base import ConvertedGraph
from gigi.graph import GraphData

NAME = "reference"


def available() -> bool:
    return True


def version() -> str | None:
    from gigi import __version__

    return f"gigi {__version__}"


def convert(graph: GraphData) -> ConvertedGraph:
    """Reference implementations read plain Python, so the 'native' graph is
    just the node list and edge triples."""
    node_ids = graph.node_ids
    return ConvertedGraph(
        native={"nodes": node_ids, "edges": graph.edge_list()},
        node_ids=node_ids,
        directed=graph.directed,
        has_weights=graph.weight_column is not None,
    )
