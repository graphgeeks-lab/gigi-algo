"""What we know about the data a method runs on.

Metadata read from a fixture's `graph.yaml`, and the deliberately cheap profile
computed from it. Nothing here may be a graph algorithm: profiling must not
cost more than the analysis it informs.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class DatasetKind(str, Enum):
    """What a fixture holds. The discriminator for `dataset.yaml`, and the same
    vocabulary a method uses to say what it consumes (`InputKind`)."""

    graph = "graph"
    vectors = "vectors"


class EdgeColumns(BaseModel):
    source: str = "source"
    target: str = "target"
    weight: str | None = None


class GraphMetadata(BaseModel):
    """`dataset.yaml` for a graph: how to read it, and what it should contain."""

    kind: Literal["graph"] = "graph"
    id: str
    description: str = ""
    directed: bool
    node_id: str = "id"
    edges: EdgeColumns = Field(default_factory=EdgeColumns)
    features: dict[str, bool] = Field(default_factory=dict)
    expected: dict[str, int] = Field(default_factory=dict)
    license: str = "CC0"


class VectorMetadata(BaseModel):
    """`dataset.yaml` for a set of vectors.

    Stored wide -- one row per vector, one column per dimension -- because a
    fixture small enough to review by eye is easier to read that way, and
    reviewability is why fixtures are CSV at all.
    """

    kind: Literal["vectors"] = "vectors"
    id: str
    description: str = ""
    id_column: str = "id"
    features: dict[str, bool] = Field(default_factory=dict)
    expected: dict[str, int] = Field(default_factory=dict)
    license: str = "CC0"


# Discriminated on `kind`, exactly as `InputSpec` is: one vocabulary for what a
# method consumes and what a fixture holds.
DatasetMetadata = Annotated[GraphMetadata | VectorMetadata, Field(discriminator="kind")]


class VectorProfile(BaseModel):
    """Cheap facts about a set of vectors. Nothing here is a similarity
    computation -- profiling must not cost more than the analysis it informs."""

    kind: Literal["vectors"] = "vectors"
    vector_count: int
    dimensions: int

    zero_vector_count: int
    has_negative_values: bool
    value_min: float | None = None
    value_max: float | None = None


class GraphProfile(BaseModel):
    """Cheap facts only. Anything that is itself a graph algorithm (components,
    diameter, triangles, communities) is out of scope on purpose."""

    kind: Literal["graph"] = "graph"
    node_count: int
    edge_count: int

    directed: bool
    weighted: bool

    self_loop_count: int
    duplicate_edge_count: int
    dangling_node_count: int

    node_id_type: str
    weight_type: str | None = None
    has_negative_weights: bool | None = None

    degree_min: float | None = None
    degree_max: float | None = None
    degree_mean: float | None = None
