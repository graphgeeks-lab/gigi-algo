"""The neutral graph layer: Arrow in memory, CSV or Parquet on disk.

Gigi does not build a graph engine. `GraphData` is a dataset container that
every adapter converts from; it has no adjacency structure of its own.

On-disk fixtures are CSV by default because a maintainer must be able to see
what changed in a pull request. Arrow is still the in-memory type, and Parquet
is read identically for datasets too large to review by eye.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pa_parquet
import yaml

from gigi.models import EdgeColumns, GraphMetadata, GraphProfile
from gigi.paths import datasets_dir

# Node identifiers are canonicalised to strings. Engines disagree about integer
# vs string keys, and that is not a divergence worth reporting -- it is noise.
NODE_ID_TYPE = "string"


class DatasetError(Exception):
    pass


@dataclass(frozen=True)
class GraphData:
    """Nodes (optional), edges, and the metadata that says how to read them."""

    edges: pa.Table
    metadata: GraphMetadata
    nodes: pa.Table | None = None

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def directed(self) -> bool:
        return self.metadata.directed

    @property
    def weight_column(self) -> str | None:
        column = self.metadata.edges.weight
        return column if column and column in self.edges.column_names else None

    @property
    def node_ids(self) -> list[str]:
        """Declared nodes if a node table exists, otherwise nodes inferred from
        edges. Order is stable: declaration order, then first-seen order."""
        if self.nodes is not None:
            return [str(v) for v in self.nodes.column(self.metadata.node_id).to_pylist()]
        seen: dict[str, None] = {}
        for source, target, _ in self.edge_list():
            seen.setdefault(source, None)
            seen.setdefault(target, None)
        return list(seen)

    def edge_list(self) -> list[tuple[str, str, float | None]]:
        """(source, target, weight) triples. Weight is None when the dataset
        declares no weight column."""
        sources = self.edges.column(self.metadata.edges.source).to_pylist()
        targets = self.edges.column(self.metadata.edges.target).to_pylist()
        column = self.weight_column
        weights = (
            self.edges.column(column).to_pylist() if column else [None] * len(sources)
        )
        return [
            (str(s), str(t), None if w is None else float(w))
            for s, t, w in zip(sources, targets, weights)
        ]


def _read_table(directory: Path, stem: str) -> pa.Table | None:
    csv_path = directory / f"{stem}.csv"
    parquet_path = directory / f"{stem}.parquet"
    if csv_path.is_file():
        return pa_csv.read_csv(csv_path)
    if parquet_path.is_file():
        return pa_parquet.read_table(parquet_path)
    return None


def load_graph(path: str | Path) -> GraphData:
    """Load a dataset directory (or a dataset id resolved under `datasets/`)."""
    directory = Path(path)
    if not directory.is_dir():
        candidate = datasets_dir() / str(path)
        if candidate.is_dir():
            directory = candidate
        else:
            raise DatasetError(f"no dataset directory at {path}")

    manifest = directory / "graph.yaml"
    if not manifest.is_file():
        raise DatasetError(f"{directory} has no graph.yaml")
    metadata = GraphMetadata.model_validate(
        yaml.safe_load(manifest.read_text(encoding="utf-8"))
    )

    edges = _read_table(directory, "edges")
    if edges is None:
        raise DatasetError(f"{directory} has no edges.csv or edges.parquet")

    for column in (metadata.edges.source, metadata.edges.target):
        if column not in edges.column_names:
            raise DatasetError(f"{directory}: edges table has no column {column!r}")

    # ADR 0003: missing endpoints are rejected, never silently dropped. CSV
    # readers surface a blank field as an empty string rather than a null, so
    # both have to be checked or the empty case slips through.
    for column in (metadata.edges.source, metadata.edges.target):
        values = edges.column(column).to_pylist()
        if any(value is None or str(value).strip() == "" for value in values):
            raise DatasetError(
                f"{directory}: edges table has null source/target values in {column!r}"
            )

    nodes = _read_table(directory, "nodes")
    if nodes is not None and metadata.node_id not in nodes.column_names:
        raise DatasetError(f"{directory}: nodes table has no column {metadata.node_id!r}")

    graph = GraphData(edges=edges, metadata=metadata, nodes=nodes)
    _check_expected_counts(directory, graph)
    return graph


def _check_expected_counts(directory: Path, graph: GraphData) -> None:
    expected = graph.metadata.expected
    if "edges" in expected and graph.edges.num_rows != expected["edges"]:
        raise DatasetError(
            f"{directory}: graph.yaml expects {expected['edges']} edges, "
            f"found {graph.edges.num_rows}"
        )
    if "nodes" in expected and len(graph.node_ids) != expected["nodes"]:
        raise DatasetError(
            f"{directory}: graph.yaml expects {expected['nodes']} nodes, "
            f"found {len(graph.node_ids)}"
        )


def graph_from_edges(
    graph_id: str,
    edges: list[list],
    directed: bool = True,
    nodes: list[str] | None = None,
) -> GraphData:
    """Build a GraphData in memory from `[source, target]` or
    `[source, target, weight]` rows. For test cases small enough to write by
    hand; anything larger belongs in `datasets/` where it can be reviewed."""
    weighted = any(len(row) > 2 for row in edges)
    columns: dict[str, list] = {
        "source": [str(row[0]) for row in edges],
        "target": [str(row[1]) for row in edges],
    }
    if weighted:
        columns["weight"] = [float(row[2]) if len(row) > 2 else 1.0 for row in edges]

    schema = pa.schema(
        [("source", pa.string()), ("target", pa.string())]
        + ([("weight", pa.float64())] if weighted else [])
    )
    metadata = GraphMetadata(
        id=graph_id,
        directed=directed,
        edges=EdgeColumns(weight="weight" if weighted else None),
    )
    node_table = (
        pa.table({"id": [str(n) for n in nodes]}, schema=pa.schema([("id", pa.string())]))
        if nodes is not None
        else None
    )
    return GraphData(edges=pa.table(columns, schema=schema), metadata=metadata, nodes=node_table)


def list_datasets() -> list[str]:
    root = datasets_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "graph.yaml").is_file())


def profile_graph(graph: GraphData) -> GraphProfile:
    """Cheap structural facts only -- a single pass over the edge list.

    Nothing here may be a graph algorithm. Components, diameter, triangles and
    communities are deliberately absent: computing them to describe a graph
    would make profiling cost more than the analysis it informs.
    """
    edges = graph.edge_list()
    node_ids = graph.node_ids

    out_degree: dict[str, int] = {node: 0 for node in node_ids}
    degree: dict[str, int] = {node: 0 for node in node_ids}
    pairs: set[tuple[str, str]] = set()

    self_loops = 0
    duplicates = 0
    weights: list[float] = []

    for source, target, weight in edges:
        out_degree[source] = out_degree.get(source, 0) + 1
        degree[source] = degree.get(source, 0) + 1
        degree[target] = degree.get(target, 0) + 1
        if source == target:
            self_loops += 1
        key = (source, target) if graph.directed else tuple(sorted((source, target)))
        if key in pairs:
            duplicates += 1
        pairs.add(key)  # type: ignore[arg-type]
        if weight is not None:
            weights.append(weight)

    degrees = list(degree.values()) or [0]
    return GraphProfile(
        node_count=len(node_ids),
        edge_count=len(edges),
        directed=graph.directed,
        weighted=graph.weight_column is not None,
        self_loop_count=self_loops,
        duplicate_edge_count=duplicates,
        dangling_node_count=sum(1 for node in node_ids if out_degree.get(node, 0) == 0),
        node_id_type=NODE_ID_TYPE,
        weight_type="double" if weights else None,
        has_negative_weights=any(w < 0 for w in weights) if weights else None,
        degree_min=float(min(degrees)),
        degree_max=float(max(degrees)),
        degree_mean=sum(degrees) / len(degrees),
    )
