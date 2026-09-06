"""One door into the fixtures, whatever kind they are.

Every fixture directory holds a `dataset.yaml` whose `kind` says what it is,
discriminated exactly the way a method's `inputs` are -- one vocabulary for
what a method consumes and what a fixture holds. Everything above this module
asks for a dataset by id and gets back whichever container fits.

The kind is declared, never inferred. A loader that guesses from the files it
finds is one bad filename away from reading a graph as something else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml
from pydantic import TypeAdapter, ValidationError

from gigi.graph import DatasetError, GraphData, load_graph, profile_graph
from gigi.models import DatasetKind, DatasetMetadata, GraphProfile, VectorProfile
from gigi.paths import datasets_dir
from gigi.vectors import VectorData, load_vectors, profile_vectors

Dataset = Union[GraphData, VectorData]
Profile = Union[GraphProfile, VectorProfile]

_METADATA = TypeAdapter(DatasetMetadata)
METADATA_FILE = "dataset.yaml"


def dataset_dir(dataset_id_or_path: str | Path) -> Path:
    """Resolve a dataset id, or a path, to its directory."""
    directory = Path(dataset_id_or_path)
    if directory.is_dir():
        return directory
    candidate = datasets_dir() / str(dataset_id_or_path)
    if candidate.is_dir():
        return candidate
    raise DatasetError(f"no dataset directory at {dataset_id_or_path}")


def read_metadata(dataset_id_or_path: str | Path) -> DatasetMetadata:
    """The `dataset.yaml` of one fixture, validated."""
    directory = dataset_dir(dataset_id_or_path)
    path = directory / METADATA_FILE
    if not path.is_file():
        raise DatasetError(f"{directory} has no {METADATA_FILE}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return _METADATA.validate_python(raw)
    except ValidationError as exc:
        raise DatasetError(f"{path}: {exc}") from exc


def dataset_kind(dataset_id_or_path: str | Path) -> DatasetKind:
    """What kind of thing this fixture holds."""
    return DatasetKind(read_metadata(dataset_id_or_path).kind)


def load_dataset(dataset_id_or_path: str | Path) -> Dataset:
    """Load a fixture, whatever kind it is."""
    directory = dataset_dir(dataset_id_or_path)
    metadata = read_metadata(directory)
    if metadata.kind == "graph":
        return load_graph(directory)
    return load_vectors(directory, metadata)


def profile_dataset(data: Dataset) -> Profile:
    """Cheap structural facts, for whichever kind this is."""
    return profile_graph(data) if isinstance(data, GraphData) else profile_vectors(data)


def describe(profile: Profile) -> str:
    """One line of shape, for a listing. The only place that has to know
    both kinds, so that nothing above it branches on kind to print a table.
    """
    if isinstance(profile, GraphProfile):
        return f"{_count(profile.node_count, 'node')}, {_count(profile.edge_count, 'edge')}"
    return f"{_count(profile.vector_count, 'vector')}, {_count(profile.dimensions, 'dim')}"


def _count(value: int, noun: str) -> str:
    return f"{value} {noun}" if value == 1 else f"{value} {noun}s"


def list_datasets(kind: DatasetKind | str | None = None) -> list[str]:
    """Every fixture id, optionally only those of one kind."""
    root = datasets_dir()
    if not root.is_dir():
        return []
    ids = sorted(p.name for p in root.iterdir() if (p / METADATA_FILE).is_file())
    if kind is None:
        return ids
    wanted = DatasetKind(kind)
    return [i for i in ids if dataset_kind(i) == wanted]
