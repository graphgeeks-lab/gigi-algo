"""Vectors as a neutral fixture, the same way graphs are.

The graph layer's shape, applied to something that is not a graph: Arrow in
memory, CSV on disk so a change is reviewable, metadata that says what the file
should contain and is checked on load.

Stored wide -- one row per vector, one column per dimension -- because a
fixture small enough to review by eye reads better that way, and reviewability
is the whole reason fixtures are CSV.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from gigi.models import VectorMetadata, VectorProfile

# Pairwise results are keyed `a|b`. An id containing the separator would make
# the key ambiguous, so the loader refuses one rather than letting a result be
# quietly unparseable.
PAIR_SEPARATOR = "|"


class VectorDataError(Exception):
    pass


@dataclass(frozen=True)
class VectorData:
    """A set of named vectors, and the metadata that says how to read them."""

    table: pa.Table
    metadata: VectorMetadata

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def ids(self) -> list[str]:
        """Vector names, in file order. Order is stable so that a backend
        keying results by index can be mapped back."""
        return [str(v) for v in self.table.column(self.metadata.id_column).to_pylist()]

    @property
    def dimension_columns(self) -> list[str]:
        return [c for c in self.table.column_names if c != self.metadata.id_column]

    @property
    def dimensions(self) -> int:
        return len(self.dimension_columns)

    def rows(self) -> dict[str, list[float]]:
        """Every vector, keyed by id."""
        columns = [self.table.column(c).to_pylist() for c in self.dimension_columns]
        return {
            name: [float(column[index]) for column in columns]
            for index, name in enumerate(self.ids)
        }


def pair_key(a: str, b: str) -> str:
    """The canonical key for an unordered pair.

    Sorted, so that a symmetric measure produces one key per pair rather than
    two that must be reconciled later.
    """
    first, second = sorted((a, b))
    return f"{first}{PAIR_SEPARATOR}{second}"


def load_vectors(directory: Path, metadata: VectorMetadata) -> VectorData:
    """Read `vectors.csv` from a fixture directory and check it against its
    metadata."""
    import pyarrow.csv as pa_csv
    import pyarrow.parquet as pa_parquet

    csv_path = directory / "vectors.csv"
    parquet_path = directory / "vectors.parquet"
    if csv_path.is_file():
        table = pa_csv.read_csv(csv_path)
    elif parquet_path.is_file():
        table = pa_parquet.read_table(parquet_path)
    else:
        raise VectorDataError(f"{directory} has no vectors.csv or vectors.parquet")

    if metadata.id_column not in table.column_names:
        raise VectorDataError(f"{directory}: no column {metadata.id_column!r}")

    data = VectorData(table=table, metadata=metadata)
    if data.dimensions == 0:
        raise VectorDataError(f"{directory}: no dimension columns beside {metadata.id_column!r}")

    ids = data.ids
    if any(not name.strip() for name in ids):
        raise VectorDataError(f"{directory}: a vector has no id")
    if len(set(ids)) != len(ids):
        raise VectorDataError(f"{directory}: duplicate vector ids")
    offenders = [name for name in ids if PAIR_SEPARATOR in name]
    if offenders:
        raise VectorDataError(
            f"{directory}: vector id(s) {offenders} contain {PAIR_SEPARATOR!r}, which is "
            f"the pair-key separator -- a pairwise result keyed on them could not be read back"
        )

    # Nulls are checked on the Arrow column rather than on the parsed rows: a
    # CSV "nan" in an otherwise integer column arrives as a null, and reading
    # it as a float would raise a TypeError from somewhere less informative
    # than here.
    if any(table.column(c).null_count for c in data.dimension_columns):
        raise VectorDataError(f"{directory}: a vector holds a missing or non-finite value")
    for vector in data.rows().values():
        if any(not math.isfinite(v) for v in vector):
            raise VectorDataError(f"{directory}: a vector holds a missing or non-finite value")

    expected = metadata.expected
    if "vectors" in expected and len(ids) != expected["vectors"]:
        raise VectorDataError(
            f"{directory}: dataset.yaml expects {expected['vectors']} vectors, found {len(ids)}"
        )
    if "dimensions" in expected and data.dimensions != expected["dimensions"]:
        raise VectorDataError(
            f"{directory}: dataset.yaml expects {expected['dimensions']} dimensions, "
            f"found {data.dimensions}"
        )
    return data


def vectors_from_rows(dataset_id: str, rows: dict[str, list[float]]) -> VectorData:
    """Build a VectorData in memory, for test cases small enough to write by hand."""
    if not rows:
        raise VectorDataError("no vectors given")
    width = len(next(iter(rows.values())))
    columns = {"id": list(rows)}
    for index in range(width):
        columns[f"d{index}"] = [float(vector[index]) for vector in rows.values()]
    return VectorData(
        table=pa.table(columns),
        metadata=VectorMetadata(id=dataset_id, expected={"vectors": len(rows), "dimensions": width}),
    )


def profile_vectors(data: VectorData) -> VectorProfile:
    """Cheap facts only: counts, shape, and the degenerate cases."""
    rows = data.rows()
    values = [v for vector in rows.values() for v in vector]
    return VectorProfile(
        vector_count=len(rows),
        dimensions=data.dimensions,
        zero_vector_count=sum(1 for vector in rows.values() if not any(vector)),
        has_negative_values=any(v < 0 for v in values),
        value_min=min(values) if values else None,
        value_max=max(values) if values else None,
    )
