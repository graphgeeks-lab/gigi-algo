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

__version__ = "0.1.0"

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
