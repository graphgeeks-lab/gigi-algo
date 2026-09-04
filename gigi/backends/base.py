"""The backend adapter contract.

An adapter owns exactly three things: whether the backend is installed, what
version it is, and how to turn `GraphData` into that backend's graph object.

It does not own algorithm calls. Those live beside the algorithm, in
`algorithms/<id>/implementations/<backend>.py`, so that adding an algorithm
never means editing `gigi/`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Union, runtime_checkable

from gigi.graph import GraphData
from gigi.vectors import VectorData

# What a backend can be handed. Kept in step with `DatasetKind` and with a
# method's `inputs`: one vocabulary for what a fixture holds, what a method
# consumes, and what a backend converts.
Dataset = Union[GraphData, VectorData]


class UnsupportedInput(Exception):
    """A backend was handed a kind of data it does not speak."""


@dataclass
class ConvertedGraph:
    """A backend-native graph plus the identity mapping back to canonical ids.

    Backends that key results by integer index (igraph, rustworkx) rely on
    `node_ids` being positionally aligned with their own vertex order.
    """

    native: Any
    node_ids: list[str]
    directed: bool
    has_weights: bool
    # What the weight is called *inside this backend's graph*, which is not the
    # dataset's column name -- adapters normalise it on conversion. An
    # implementation that passes the column name through works only as long as
    # every fixture happens to call its column "weight"; `road-distances-small`
    # is the fixture that stops it.
    weight_attribute: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def result_keys(self) -> list[str]:
        """What a result of this run should be keyed by: one score per node."""
        return self.node_ids

    @property
    def keys_are_complete(self) -> bool:
        """Every node must get a score, so a missing one is an error."""
        return True

    def index_of(self, node_id: str) -> int:
        return self.node_ids.index(node_id)


@dataclass
class ConvertedVectors:
    """Backend-native vectors, plus the ids they belong to.

    The second thing a backend can be handed, and the reason `ConvertedGraph`
    is not the only shape: a similarity measure consumes vectors and returns
    one number per *pair*, so the keys of its result are not the keys of its
    input.
    """

    native: object
    ids: list[str]
    dimensions: int
    notes: list[str] = field(default_factory=list)

    @property
    def result_keys(self) -> list[str]:
        """Pair ids in canonical `a|b` form: every unordered pair, once."""
        from gigi.vectors import pair_key

        return [
            pair_key(a, b)
            for index, a in enumerate(self.ids)
            for b in self.ids[index + 1:]
        ]

    @property
    def keys_are_complete(self) -> bool:
        """A measure may legitimately decline a pair -- a zero vector has no
        direction -- so a missing key is a finding for the comparator rather
        than an error here."""
        return False


def require_graph(backend: str, data: Dataset) -> GraphData:
    """Refuse non-graph input by name rather than failing somewhere deeper.

    Not every backend speaks every kind of data, and that is fine. What is
    not fine is a NetworkX adapter half-converting a set of vectors and
    raising an AttributeError three frames down.
    """
    if not isinstance(data, GraphData):
        raise UnsupportedInput(f"{backend} takes a graph, not {type(data).__name__}")
    return data


def require_vectors(backend: str, data: Dataset) -> VectorData:
    """The mirror of `require_graph`, for backends that take vectors."""
    if not isinstance(data, VectorData):
        raise UnsupportedInput(f"{backend} takes vectors, not {type(data).__name__}")
    return data


@runtime_checkable
class BackendAdapter(Protocol):
    """What every adapter module provides. Documentation more than typing:
    adapters are plain modules, and this is the shape they must have."""

    NAME: str

    def available(self) -> bool: ...

    def version(self) -> str | None: ...

    def convert(self, data: Dataset) -> ConvertedGraph | ConvertedVectors: ...
