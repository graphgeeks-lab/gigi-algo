"""The reference backend: no third-party library, always available.

Reference implementations are the oracle every other backend is compared
against, and they are teaching artifacts first. They optimise for reading, not
for speed. See ADR 0002.
"""

from __future__ import annotations

from gigi.backends.base import ConvertedGraph, ConvertedVectors, Dataset
from gigi.graph import GraphData
from gigi.vectors import VectorData

NAME = "reference"


def available() -> bool:
    return True


def version() -> str | None:
    from gigi import __version__

    return f"gigi {__version__}"


def convert(data: Dataset) -> ConvertedGraph | ConvertedVectors:
    """Reference implementations read plain Python, so 'native' is a list or
    a dict.

    The reference backend is the only one that accepts every kind of input,
    because being the oracle for every method is its whole job.
    """
    if isinstance(data, VectorData):
        return ConvertedVectors(
            native=data.rows(),
            ids=data.ids,
            dimensions=data.dimensions,
        )

    graph: GraphData = data
    node_ids = graph.node_ids
    return ConvertedGraph(
        native={"nodes": node_ids, "edges": graph.edge_list()},
        node_ids=node_ids,
        directed=graph.directed,
        has_weights=graph.weight_column is not None,
    )
