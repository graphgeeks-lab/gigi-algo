"""Load algorithm specs and their per-engine implementations.

An algorithm is a directory. Nothing is registered in code: adding
`algorithms/<id>/algorithm.yaml` is the entire registration step.
"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import yaml
from pydantic import ValidationError

from gigi.models import AlgorithmSpec, Family
from gigi.paths import algorithms_dir, families_file


class RegistryError(Exception):
    pass


# --------------------------------------------------------------------------
# Families
#
# A family is not a folder. It answers a question -- "in what order do I reach
# the nodes?", "which nodes hold the network together?" -- and an algorithm
# belongs to it when it answers that question. Keeping them in one small file
# rather than as free-text on each spec means the taxonomy can be navigated,
# and that a typo is an error rather than a new family.
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _families() -> dict[str, Family]:
    path = families_file()
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    families: dict[str, Family] = {}
    for entry in raw:
        try:
            family = Family.model_validate(entry)
        except ValidationError as exc:
            raise RegistryError(f"{path}: {exc}") from exc
        if family.id in families:
            raise RegistryError(f"{path}: duplicate family id {family.id!r}")
        families[family.id] = family
    return families


def list_families() -> list[Family]:
    # Sorted by id, which is what people type and what the tables show first.
    return sorted(_families().values(), key=lambda f: f.id)


def load_family(family_id: str) -> Family:
    """One family, or an error naming the ones that exist."""
    families = _families()
    if family_id not in families:
        known = ", ".join(sorted(families)) or "none"
        raise RegistryError(f"unknown family {family_id!r} (known: {known})")
    return families[family_id]


def family_exists(family_id: str) -> bool:
    return family_id in _families()


def family_lineage(family_id: str) -> list[Family]:
    """This family and its ancestors, outermost first."""
    lineage: list[Family] = []
    seen: set[str] = set()
    current: str | None = family_id
    while current and current not in seen and family_exists(current):
        seen.add(current)
        family = load_family(current)
        lineage.append(family)
        current = family.parent
    return list(reversed(lineage))


def algorithms_in_family(family_id: str) -> list[str]:
    return [a for a in list_algorithms() if load_algorithm(a).family == family_id]


def list_algorithms() -> list[str]:
    """Every algorithm id in the registry, sorted. Directories starting with
    `_` (`_schema`, `_template`) are infrastructure, not algorithms."""
    root = algorithms_dir()
    if not root.is_dir():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "algorithm.yaml").is_file()
    )


@lru_cache(maxsize=None)
def load_algorithm(algorithm_id: str) -> AlgorithmSpec:
    """Read and validate one `algorithm.yaml`.

    Validation errors are re-raised with the file path attached, because the
    person who sees them is usually editing that file.
    """
    path = algorithms_dir() / algorithm_id / "algorithm.yaml"
    if not path.is_file():
        known = ", ".join(list_algorithms()) or "none"
        raise RegistryError(f"unknown algorithm {algorithm_id!r} (known: {known})")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        spec = AlgorithmSpec.model_validate(raw)
    except ValidationError as exc:  # point the contributor at the field
        raise RegistryError(f"{path}: {exc}") from exc

    if spec.id != algorithm_id:
        raise RegistryError(
            f"{path}: id is {spec.id!r} but the directory is {algorithm_id!r}"
        )
    return spec


# Named here so `review` can report "no igraph implementation yet" without
# importing the adapter package, which pulls in the engines.
ENGINE_NAMES = ("reference", "networkx", "igraph", "rustworkx")


def algorithm_dir(algorithm_id: str) -> Path:
    return algorithms_dir() / algorithm_id


def implementation_path(algorithm_id: str, engine: str) -> Path:
    return algorithm_dir(algorithm_id) / "implementations" / f"{engine}.py"


def has_implementation(algorithm_id: str, engine: str) -> bool:
    return implementation_path(algorithm_id, engine).is_file()


def implemented_engines(algorithm_id: str) -> list[str]:
    """Engines this algorithm has a file for, whether installed or not."""
    impl_dir = algorithm_dir(algorithm_id) / "implementations"
    if not impl_dir.is_dir():
        return []
    return sorted(
        p.stem for p in impl_dir.glob("*.py") if not p.stem.startswith("_")
    )


@lru_cache(maxsize=None)
def load_implementation(algorithm_id: str, engine: str) -> ModuleType:
    """Import `algorithms/<id>/implementations/<engine>.py` by path.

    Loading by path rather than by package name keeps `algorithms/` a plain
    content directory: no `__init__.py`, no import side effects, no packaging.
    """
    path = implementation_path(algorithm_id, engine)
    if not path.is_file():
        raise RegistryError(f"{algorithm_id} has no {engine} implementation ({path})")

    module_name = f"gigi_impl_{algorithm_id}_{engine}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RegistryError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise RegistryError(f"{path} must define run(graph, params)")
    return module
