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
# graph-only by construction. `algorithm`, `algorithms` and `inspect_graph`
# were kept alongside them for a v0.1 that never shipped -- six names for four
# functions, in a codebase whose rule is one fact in one place -- and were
# removed before anyone could depend on them.
method = load_method
methods = list_methods
datasets = list_datasets
inspect = profile_dataset

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
    "method",
    "methods",
    "available_backends",
    "compare",
    "datasets",
    "backend_versions",
    "inspect",
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
