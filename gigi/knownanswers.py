"""Known-answer cases: the oracle's only independent check.

Every backend is compared against the reference implementation, so if the
reference is wrong, every green check is meaningless. The conformance suite
cannot catch that -- it would be checking the code against itself.

`methods/<id>/tests/expected.yaml` is the way out. Each case names a small
dataset, the parameters, the expected scores, and -- the part that matters --
`derived`: where the expected answer came from. Symmetry, a closed form, a hand
calculation, a worked example in a paper. Never "I ran it". A case derived by
running the code proves nothing; a case derived from the definition proves the
reference implements the definition.

Contributors write YAML, not pytest. The suite is generated from it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from gigi import registry
from gigi.data import Dataset, load_dataset
from gigi.graph import graph_from_edges
from gigi.harness import resolve_parameters, run
from gigi.models import KnownAnswer, RunStatus
from gigi.vectors import vectors_from_rows


class KnownAnswerError(Exception):
    pass


def cases_path(method_id: str) -> Path:
    return registry.method_dir(method_id) / "tests" / "expected.yaml"


@lru_cache(maxsize=None)
def load_cases(method_id: str) -> list[KnownAnswer]:
    """Every known-answer case for one algorithm, or an empty list if the file
    does not exist yet."""
    path = cases_path(method_id)
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = raw.get("cases", []) if isinstance(raw, dict) else raw

    loaded: list[KnownAnswer] = []
    seen: set[str] = set()
    for entry in cases:
        try:
            case = KnownAnswer.model_validate(entry)
        except ValidationError as exc:
            raise KnownAnswerError(f"{path}: {exc}") from exc
        if case.id in seen:
            raise KnownAnswerError(f"{path}: duplicate case id {case.id!r}")
        if case.data() is None:
            raise KnownAnswerError(
                f"{path}: case {case.id!r} names no data -- give it a dataset, a graph or vectors"
            )
        seen.add(case.id)
        loaded.append(case)
    return loaded


def data_for(case: KnownAnswer) -> Dataset:
    """The fixture the case names, or its inline data built in memory."""
    if case.dataset is not None:
        return load_dataset(case.dataset)
    if case.vectors is not None:
        return vectors_from_rows(f"case:{case.id}", case.vectors.rows)
    assert case.graph is not None
    return graph_from_edges(
        f"case:{case.id}",
        case.graph.edges,
        directed=case.graph.directed,
        nodes=case.graph.nodes or None,
    )


@dataclass
class CaseResult:
    """One case on one backend: passed, or why not."""

    case_id: str
    backend: str
    passed: bool
    detail: str = ""


def run_case(method_id: str, case: KnownAnswer, backend: str = "reference") -> CaseResult:
    """Run one backend on one case and compare against the expected scores."""
    spec = registry.load_method(method_id)
    data = data_for(case)
    # Pinned the way verification pins them: a closed form at 1e-9 is not a fair
    # test of a backend left at its own 1e-6 default. The case's own parameters
    # win over the pins.
    parameters = resolve_parameters(spec, data, overrides=case.parameters, explicit=True)
    try:
        result = run(spec, backend, data, parameters=parameters, allow_frontier=True)
    except KeyError as exc:  # unknown backend name; the harness raises, we report
        return CaseResult(case.id, backend, False, f"unknown backend: {exc}")

    if result.status != RunStatus.ok or result.result is None:
        return CaseResult(case.id, backend, False, f"{result.status.value}: {result.error}")

    scores = result.result.scores
    missing = sorted(set(case.expected) - set(scores))
    if missing:
        return CaseResult(case.id, backend, False, f"no score for {missing}")

    worst = max(
        ((key, abs(scores[key] - value)) for key, value in case.expected.items()),
        key=lambda pair: pair[1],
        default=(None, 0.0),
    )
    if worst[1] > case.tolerance:
        node = worst[0]
        return CaseResult(
            case.id,
            backend,
            False,
            f"{node}: expected {case.expected[node]!r}, got {scores[node]!r} "
            f"(off by {worst[1]:.3e}, tolerance {case.tolerance:g})",
        )
    return CaseResult(case.id, backend, True)
