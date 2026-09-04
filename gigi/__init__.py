"""Gigi -- an executable registry of graph algorithm semantics.

The Python API is the surface everything else is built on; the CLI and any
future agent tools call exactly these functions.

    import gigi

    spec    = gigi.algorithm("pagerank")
    graph   = gigi.load_graph("datasets/weighted-small")
    profile = gigi.inspect_graph(graph)
    result  = gigi.run("pagerank", engine="networkx", graph=graph)
    report  = gigi.verify("pagerank")
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

from gigi.adapters import available_engines, engine_versions
from gigi.graph import GraphData, list_datasets, load_graph, profile_graph
from gigi.harness import compare, run, verify
from gigi.models import (
    AlgorithmSpec,
    Comparison,
    GraphProfile,
    RunResult,
    VerificationReport,
)
from gigi.registry import list_algorithms, load_algorithm

# Read-aloud aliases used in the docs and by the CLI.
algorithm = load_algorithm
algorithms = list_algorithms
datasets = list_datasets
inspect_graph = profile_graph

__all__ = [
    "AlgorithmSpec",
    "Comparison",
    "GraphData",
    "GraphProfile",
    "RunResult",
    "VerificationReport",
    "__version__",
    "algorithm",
    "algorithms",
    "available_engines",
    "compare",
    "datasets",
    "engine_versions",
    "inspect_graph",
    "list_algorithms",
    "list_datasets",
    "load_algorithm",
    "load_graph",
    "profile_graph",
    "run",
    "verify",
]
