"""Engine registry.

A dict, not a plugin system. Adding an engine is: write the module, add the
line. If that ever becomes painful we will know, because the line will be
somewhere other than here.
"""

from __future__ import annotations

from types import ModuleType

from gigi.adapters import igraph, networkx, reference, rustworkx
from gigi.adapters.base import ConvertedGraph, EngineAdapter

ENGINES: dict[str, ModuleType] = {
    "reference": reference,
    "networkx": networkx,
    "igraph": igraph,
    "rustworkx": rustworkx,
}


def get_engine(name: str) -> ModuleType:
    if name not in ENGINES:
        raise KeyError(f"unknown engine {name!r} (known: {', '.join(ENGINES)})")
    return ENGINES[name]


def available_engines() -> list[str]:
    """Engines whose library is actually importable in this environment."""
    return [name for name, module in ENGINES.items() if module.available()]


def engine_versions() -> dict[str, str | None]:
    return {name: module.version() for name, module in ENGINES.items() if module.available()}


__all__ = [
    "ENGINES",
    "ConvertedGraph",
    "EngineAdapter",
    "available_engines",
    "engine_versions",
    "get_engine",
]
