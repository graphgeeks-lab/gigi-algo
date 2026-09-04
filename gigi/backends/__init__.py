"""Backend registry.

A dict, not a plugin system. Adding a backend is: write the module, add the
line. If that ever becomes painful we will know, because the line will be
somewhere other than here.
"""

from __future__ import annotations

from types import ModuleType

from gigi.backends import igraph, networkx, reference, rustworkx, scipy, sklearn
from gigi.backends.base import BackendAdapter, ConvertedGraph, ConvertedVectors

BACKENDS: dict[str, ModuleType] = {
    "reference": reference,
    "networkx": networkx,
    "igraph": igraph,
    "rustworkx": rustworkx,
    # Vector backends. A backend is not "a graph library" -- it is whatever
    # can be handed a dataset and asked for an answer.
    "scipy": scipy,
    "sklearn": sklearn,
}


def get_backend(name: str) -> ModuleType:
    if name not in BACKENDS:
        raise KeyError(f"unknown backend {name!r} (known: {', '.join(BACKENDS)})")
    return BACKENDS[name]


def available_backends() -> list[str]:
    """Backends whose library is actually importable in this environment."""
    return [name for name, module in BACKENDS.items() if module.available()]


def backend_versions() -> dict[str, str | None]:
    return {name: module.version() for name, module in BACKENDS.items() if module.available()}


__all__ = [
    "BACKENDS",
    "BackendAdapter",
    "ConvertedGraph",
    "ConvertedVectors",
    "available_backends",
    "backend_versions",
    "get_backend",
]
