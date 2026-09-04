"""Gigi -- an executable registry of graph algorithm semantics.

The Python API is the surface everything else is built on; the CLI and any
future agent tools call exactly these functions.

    import gigi

    spec    = gigi.method("pagerank")
    data    = gigi.load_dataset("weighted-small")
    profile = gigi.inspect(data)
    result  = gigi.run("pagerank", "networkx", data)
    report  = gigi.verify("pagerank")

`load_dataset` takes a fixture of any kind -- a graph, or the vectors a
similarity measure consumes -- and `run` never asks which it was given.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _installed_version

# One source of truth for the version: pyproject.toml. `uv version 0.2.0`
# edits that file; this reads the result from the installed metadata, so there
# is nothing here to forget to bump. The fallback only matters when the package
# is imported from a checkout that was never installed.
try:
    __version__ = _installed_version("gigi-algo")
except PackageNotFoundError:  # pragma: no cover - uninstalled checkout
    __version__ = "0.0.0+uninstalled"

from gigi.backends import available_backends, backend_versions
from gigi.data import list_datasets, load_dataset, profile_dataset
from gigi.graph import GraphData, load_graph, profile_graph
from gigi.harness import compare, run, verify
from gigi.models import (
    MethodSpec,
    Comparison,
    GraphProfile,
    VectorProfile,
    RunResult,
    VerificationReport,
)
from gigi.registry import list_methods, load_method
from gigi.vectors import VectorData

# Read-aloud aliases. `method` is canonical now that the registry is not
# graph-only by construction; `algorithm` stays because it is the word a
# reader reaches for when the method happens to be one.
method = load_method
methods = list_methods
algorithm = load_method
algorithms = list_methods
datasets = list_datasets
inspect = profile_dataset
# Kept: it was the v0.1 name, and a graph is still the common case.
inspect_graph = profile_graph

__all__ = [
    "MethodSpec",
    "Comparison",
    "GraphData",
    "GraphProfile",
    "VectorData",
    "VectorProfile",
    "RunResult",
    "VerificationReport",
    "__version__",
    "algorithm",
    "algorithms",
    "method",
    "methods",
    "available_backends",
    "compare",
    "datasets",
    "backend_versions",
    "inspect",
    "inspect_graph",
    "load_dataset",
    "profile_dataset",
    "list_methods",
    "list_datasets",
    "load_method",
    "load_graph",
    "profile_graph",
    "run",
    "verify",
]
