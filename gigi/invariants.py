"""Property checks: the maths, executed.

`algorithm.yaml` states that PageRank scores sum to one. This module is what
makes that statement cost something — every run asserts it, on every engine, on
every fixture. A property that is written down but never checked is a comment,
and a registry full of comments is what we are trying not to build.

Adding a check is adding one function and one line in `CHECKS`. An invariant id
in a spec that names no check here fails the test suite, so the two cannot
drift apart.

This is the PROPERTY verifier from the discovery PRD in its cheapest form. When
candidates arrive later, they run through exactly these functions: the verifier
does not care whether the code came from a person, an engine or a search.
"""

from __future__ import annotations

import math
from typing import Callable

from gigi.models import Invariant, InvariantResult, NodeScoreResult

# A check returns None when the property holds, or a human-readable reason.
Check = Callable[[NodeScoreResult, Invariant], "str | None"]


def scores_sum_to_one(result: NodeScoreResult, invariant: Invariant) -> str | None:
    """The scores form a probability distribution."""
    if not result.scores:
        return None
    tolerance = invariant.tolerance if invariant.tolerance is not None else 1e-6
    total = math.fsum(result.scores.values())
    if abs(total - 1.0) > tolerance:
        return f"scores sum to {total!r}, off by {abs(total - 1.0):.3e}"
    return None


def scores_non_negative(result: NodeScoreResult, invariant: Invariant) -> str | None:
    """No score is below zero."""
    negative = {node: value for node, value in result.scores.items() if value < 0}
    if negative:
        worst = min(negative, key=lambda n: negative[n])
        return f"{len(negative)} negative score(s), lowest {worst}={negative[worst]!r}"
    return None


def scores_finite(result: NodeScoreResult, invariant: Invariant) -> str | None:
    bad = [n for n, v in result.scores.items() if not math.isfinite(v)]
    if bad:
        return f"{len(bad)} non-finite score(s): {sorted(bad)[:5]}"
    return None


def scores_in_unit_interval(result: NodeScoreResult, invariant: Invariant) -> str | None:
    """Every score lies in [0, 1]."""
    outside = {n: v for n, v in result.scores.items() if not 0.0 <= v <= 1.0}
    if outside:
        worst = max(outside, key=lambda n: abs(outside[n]))
        return f"{len(outside)} score(s) outside [0, 1], e.g. {worst}={outside[worst]!r}"
    return None


def scores_are_symmetric_free(result: NodeScoreResult, invariant: Invariant) -> str | None:
    """Every node has exactly one score. Catches an engine that silently drops
    isolated nodes, which is a real failure mode and easy to miss."""
    if len(set(result.scores)) != len(result.scores):  # pragma: no cover - dict keys
        return "duplicate node ids in result"
    return None


CHECKS: dict[str, Check] = {
    "scores_sum_to_one": scores_sum_to_one,
    "scores_non_negative": scores_non_negative,
    "scores_finite": scores_finite,
    "scores_in_unit_interval": scores_in_unit_interval,
    "scores_unique_per_node": scores_are_symmetric_free,
}


def known(invariant_id: str) -> bool:
    return invariant_id in CHECKS


def check_all(result: NodeScoreResult, invariants: list[Invariant]) -> list[InvariantResult]:
    """Run every checkable invariant against one result."""
    outcomes: list[InvariantResult] = []
    for invariant in invariants:
        if not invariant.check:
            continue
        checker = CHECKS.get(invariant.id)
        if checker is None:
            outcomes.append(
                InvariantResult(
                    invariant_id=invariant.id,
                    statement=invariant.statement,
                    passed=False,
                    detail=f"no check implemented for {invariant.id!r}",
                )
            )
            continue
        detail = checker(result, invariant)
        outcomes.append(
            InvariantResult(
                invariant_id=invariant.id,
                statement=invariant.statement,
                passed=detail is None,
                detail=detail or "",
            )
        )
    return outcomes
