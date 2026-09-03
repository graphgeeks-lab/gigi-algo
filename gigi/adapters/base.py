"""The engine adapter contract.

An adapter owns exactly three things: whether the engine is installed, what
version it is, and how to turn `GraphData` into that engine's graph object.

It does not own algorithm calls. Those live beside the algorithm, in
`algorithms/<id>/implementations/<engine>.py`, so that adding an algorithm
never means editing `gigi/`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from gigi.graph import GraphData


@dataclass
class ConvertedGraph:
    """An engine-native graph plus the identity mapping back to canonical ids.

    Engines that key results by integer index (igraph, rustworkx) rely on
    `node_ids` being positionally aligned with their own vertex order.
    """

    native: Any
    node_ids: list[str]
    directed: bool
    has_weights: bool
    notes: list[str] = field(default_factory=list)

    def index_of(self, node_id: str) -> int:
        return self.node_ids.index(node_id)


@runtime_checkable
class EngineAdapter(Protocol):
    """What every adapter module provides. Documentation more than typing:
    adapters are plain modules, and this is the shape they must have."""

    NAME: str

    def available(self) -> bool: ...

    def version(self) -> str | None: ...

    def convert(self, graph: GraphData) -> ConvertedGraph: ...
