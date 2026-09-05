"""Load algorithm specs and their per-backend implementations.

An algorithm is a directory. Nothing is registered in code: adding
`methods/<id>/method.yaml` is the entire registration step.
"""

from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import yaml
from pydantic import ValidationError

from gigi.models import DomainSpec, Family, Maturity, MethodSpec, ProblemSpec
from gigi.paths import domains_file, families_file, methods_dir, problems_dir


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


# --------------------------------------------------------------------------
# Problems
#
# A problem is a question, stated without reference to any method. It exists so
# that "which method should I use?" has somewhere to start that is not a method
# name, and so that `gigi why` can say what a method does *not* answer by
# naming other people's questions rather than waving vaguely.
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _problems() -> dict[str, ProblemSpec]:
    directory = problems_dir()
    if not directory.is_dir():
        return {}
    problems: dict[str, ProblemSpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            problem = ProblemSpec.model_validate(raw)
        except ValidationError as exc:
            raise RegistryError(f"{path}: {exc}") from exc
        if problem.id != path.stem:
            raise RegistryError(f"{path}: id is {problem.id!r} but the file is {path.stem!r}")
        problems[problem.id] = problem
    return problems


def list_problems() -> list[ProblemSpec]:
    """Every problem, sorted by id."""
    return sorted(_problems().values(), key=lambda p: p.id)


def load_problem(problem_id: str) -> ProblemSpec:
    """One problem, or an error naming the ones that exist."""
    problems = _problems()
    if problem_id not in problems:
        known = ", ".join(sorted(problems)) or "none"
        raise RegistryError(f"unknown problem {problem_id!r} (known: {known})")
    return problems[problem_id]


def problem_exists(problem_id: str) -> bool:
    return problem_id in _problems()


def methods_for_problem(problem_id: str) -> list[str]:
    """Which methods claim to solve this."""
    return [m for m in list_methods() if problem_id in load_method(m).problems]


@lru_cache(maxsize=1)
def _domains() -> dict[str, DomainSpec]:
    path = domains_file()
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    domains: dict[str, DomainSpec] = {}
    for entry in raw:
        try:
            domain = DomainSpec.model_validate(entry)
        except ValidationError as exc:
            raise RegistryError(f"{path}: {exc}") from exc
        if domain.id in domains:
            raise RegistryError(f"{path}: duplicate domain id {domain.id!r}")
        domains[domain.id] = domain
    return domains


def list_domains() -> list[DomainSpec]:
    """Every domain, sorted by id."""
    return sorted(_domains().values(), key=lambda d: d.id)


def load_domain(domain_id: str) -> DomainSpec:
    """One domain, or an error naming the ones that exist."""
    domains = _domains()
    if domain_id not in domains:
        known = ", ".join(sorted(domains)) or "none"
        raise RegistryError(f"unknown domain {domain_id!r} (known: {known})")
    return domains[domain_id]


def domain_exists(domain_id: str) -> bool:
    return domain_id in _domains()


def domain_of(method_id_or_spec) -> str:
    """A method's domain, derived through its family.

    Not stored on the method: the family already knows, and two fields naming
    one fact drift apart. Everything that groups methods by domain -- the site,
    `gigi list --domain` -- comes through here.
    """
    spec = (
        method_id_or_spec
        if isinstance(method_id_or_spec, MethodSpec)
        else load_method(method_id_or_spec)
    )
    return load_family(spec.family).domain


def families_in_domain(domain_id: str) -> list[str]:
    return [f.id for f in list_families() if f.domain == domain_id]


def methods_in_domain(domain_id: str) -> list[str]:
    return [m for m in list_methods() if domain_of(m) == domain_id]


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


def methods_in_family(family_id: str) -> list[str]:
    return [a for a in list_methods() if load_method(a).family == family_id]


def list_methods() -> list[str]:
    """Every algorithm id in the registry, sorted. Directories starting with
    `_` (`_schema`, `_template`) are infrastructure, not algorithms."""
    root = methods_dir()
    if not root.is_dir():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "method.yaml").is_file()
    )


@lru_cache(maxsize=None)
def load_method(method_id: str) -> MethodSpec:
    """Read and validate one `method.yaml`.

    Validation errors are re-raised with the file path attached, because the
    person who sees them is usually editing that file.
    """
    path = methods_dir() / method_id / "method.yaml"
    if not path.is_file():
        known = ", ".join(list_methods()) or "none"
        raise RegistryError(f"unknown algorithm {method_id!r} (known: {known})")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        spec = MethodSpec.model_validate(raw)
    except ValidationError as exc:  # point the contributor at the field
        raise RegistryError(f"{path}: {exc}") from exc

    if spec.id != method_id:
        raise RegistryError(
            f"{path}: id is {spec.id!r} but the directory is {method_id!r}"
        )
    return spec


# Named here so `review` can report "no igraph implementation yet" without
# importing the adapter package, which pulls in the backends. Each entry says
# what the backend can be handed, so that a review never suggests writing a
# NetworkX implementation of a measure over vectors.
BACKEND_INPUT_KINDS: dict[str, tuple[str, ...]] = {
    "reference": ("graph", "vectors"),
    "networkx": ("graph",),
    "igraph": ("graph",),
    "rustworkx": ("graph",),
    "scipy": ("vectors",),
    "sklearn": ("vectors",),
}
BACKEND_NAMES = tuple(BACKEND_INPUT_KINDS)


def plausible_backends(spec: MethodSpec) -> list[str]:
    """Backends that could take this method's input, whether or not anyone has
    written the implementation.

    The set a missing implementation is measured against. A method's own
    `backends:` map may additionally rule one out with a reason, and that is
    respected: an explicit `supported: false` is an answer, not a gap.
    """
    kinds = {str(i.kind) for i in spec.inputs}
    declined = {name for name, support in spec.backends.items() if not support.supported}
    return sorted(
        name
        for name, accepted in BACKEND_INPUT_KINDS.items()
        if kinds & set(accepted) and name not in declined
    )


def set_maturity(method_id: str, maturity: Maturity) -> Path:
    """Rewrite the `maturity:` line of one method.yaml.

    The only write this package makes to the registry, and it exists so that
    promotion is a checked action rather than a hand edit that skips the
    checks. Everything else about the file is left exactly as the contributor
    wrote it.
    """
    path = method_dir(method_id) / "method.yaml"
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"^maturity:.*$", f"maturity: {maturity.value}", text, count=1, flags=re.M
    )
    if count != 1:
        raise RegistryError(f"{path}: could not find a `maturity:` line to rewrite")
    path.write_text(updated, encoding="utf-8")
    load_method.cache_clear()
    return path


def method_exists(method_id: str) -> bool:
    """Is this method in the registry?"""
    return method_id in set(list_methods())


def method_dir(method_id: str) -> Path:
    return methods_dir() / method_id


def implementation_path(method_id: str, backend: str) -> Path:
    return method_dir(method_id) / "implementations" / f"{backend}.py"


def has_implementation(method_id: str, backend: str) -> bool:
    return implementation_path(method_id, backend).is_file()


def implemented_backends(method_id: str) -> list[str]:
    """Backends this algorithm has a file for, whether installed or not."""
    impl_dir = method_dir(method_id) / "implementations"
    if not impl_dir.is_dir():
        return []
    return sorted(
        p.stem for p in impl_dir.glob("*.py") if not p.stem.startswith("_")
    )


@lru_cache(maxsize=None)
def load_implementation(method_id: str, backend: str) -> ModuleType:
    """Import `methods/<id>/implementations/<backend>.py` by path.

    Loading by path rather than by package name keeps `methods/` a plain
    content directory: no `__init__.py`, no import side effects, no packaging.
    """
    path = implementation_path(method_id, backend)
    if not path.is_file():
        raise RegistryError(f"{method_id} has no {backend} implementation ({path})")

    module_name = f"gigi_impl_{method_id}_{backend}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RegistryError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise RegistryError(f"{path} must define run(graph, params)")
    return module
