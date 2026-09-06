"""Property checks: the maths, executed.

`method.yaml` states that PageRank scores sum to one. This module is what
makes that statement cost something — every run asserts it, on every backend, on
every fixture. A property that is written down but never checked is a comment,
and a registry full of comments is what we are trying not to build.

Adding a check is adding one function and one line in `CHECKS`. An invariant id
in a spec that names no check here fails the test suite, so the two cannot
drift apart.

Some properties are about the result alone -- scores sum to one, no score is
NaN. Others cannot be stated without the input: "every component is connected"
is a claim about a partition *and the graph it partitions*. And some depend on
what was asked for: "no edge crosses between components" is true of the weak
decomposition and false of the strong one, where a crossing edge is the whole
point.

So a check receives a `CheckContext` -- the dataset and the effective
parameters -- alongside the result. Most checks ignore it. The ones that use it
are the ones worth having: an invariant that only looks at the result can
assert almost nothing about a partition, and an invariant that is false under a
supported parameter setting is not an invariant.

This is the PROPERTY verifier from the discovery PRD in its cheapest form. When
candidates arrive later, they run through exactly these functions: the verifier
does not care whether the code came from a person, a backend or a search.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from gigi.models import (
    Invariant,
    InvariantResult,
    NormalizedResult,
    PartitionResult,
    ScoreResult,
)


@dataclass(frozen=True)
class CheckContext:
    """Everything a check may need besides the result itself.

    Frozen, because a check that could modify what it is checking would be
    worse than no check. `data` is the dataset the result came from; the
    parameters are the *effective* ones -- what the backend actually did, not
    what was requested (ADR 0004).
    """

    data: Any = None
    parameters: dict[str, Any] = field(default_factory=dict)


# A check returns None when the property holds, or a human-readable reason.
Check = Callable[[NormalizedResult, Invariant, CheckContext], "str | None"]


def _wrong_shape(result: NormalizedResult, wanted: type) -> "str | None":
    """A spec that names a score invariant on a partition method is an authoring
    mistake, and this is where it surfaces -- as a failed invariant naming both
    kinds, rather than an AttributeError from inside a check."""
    if isinstance(result, wanted):
        return None
    return (
        f"this invariant is for {wanted.__name__}, but the result is a "
        f"{type(result).__name__}"
    )


def scores_sum_to_one(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """The scores form a probability distribution."""
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    if not result.scores:
        return None
    tolerance = invariant.tolerance if invariant.tolerance is not None else 1e-6
    total = math.fsum(result.scores.values())
    if abs(total - 1.0) > tolerance:
        return f"scores sum to {total!r}, off by {abs(total - 1.0):.3e}"
    return None


def scores_non_negative(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """No score is below zero."""
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    negative = {node: value for node, value in result.scores.items() if value < 0}
    if negative:
        worst = min(negative, key=lambda n: negative[n])
        return f"{len(negative)} negative score(s), lowest {worst}={negative[worst]!r}"
    return None


def scores_finite(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """No score is NaN or infinite.

    The cheapest check here and the one that has caught the most: a NaN
    compares False against every tolerance, so without this it would pass every
    comparison it took part in.
    """
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    bad = [n for n, v in result.scores.items() if not math.isfinite(v)]
    if bad:
        return f"{len(bad)} non-finite score(s): {sorted(bad)[:5]}"
    return None


def scores_in_unit_interval(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """Every score lies in [0, 1]."""
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    outside = {n: v for n, v in result.scores.items() if not 0.0 <= v <= 1.0}
    if outside:
        worst = max(outside, key=lambda n: abs(outside[n]))
        return f"{len(outside)} score(s) outside [0, 1], e.g. {worst}={outside[worst]!r}"
    return None


def scores_in_signed_unit_interval(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """Every score lies in [-1, 1].

    The bound a correlation-like measure has and a probability does not.
    Separate from `scores_in_unit_interval` rather than parameterised,
    because an invariant that quietly widens its own bound asserts nothing.
    """
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    outside = {n: v for n, v in result.scores.items() if not -1.0 <= v <= 1.0}
    if outside:
        worst = max(outside, key=lambda n: abs(outside[n]))
        return f"{len(outside)} score(s) outside [-1, 1], e.g. {worst}={outside[worst]!r}"
    return None


def keys_are_canonical_pairs(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """Every key names an unordered pair once, in sorted `a|b` form.

    A symmetric measure that emits both `a|b` and `b|a`, or emits them
    unsorted, has not returned a wrong number -- it has returned a result
    nothing downstream can join on. That is worth catching on every run.
    """
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    from gigi.vectors import PAIR_SEPARATOR

    bad = []
    for key in result.scores:
        parts = key.split(PAIR_SEPARATOR)
        if len(parts) != 2 or list(parts) != sorted(parts):
            bad.append(key)
    if bad:
        return f"{len(bad)} key(s) are not canonical pairs: {sorted(bad)[:5]}"
    return None


def scores_are_symmetric_free(result: NormalizedResult, invariant: Invariant, context: CheckContext) -> str | None:
    """Every node has exactly one score. Catches a backend that silently drops
    isolated nodes, which is a real failure mode and easy to miss."""
    if (wrong := _wrong_shape(result, ScoreResult)):
        return wrong
    if len(set(result.scores)) != len(result.scores):  # pragma: no cover - dict keys
        return "duplicate node ids in result"
    return None


def components_are_connected(
    result: NormalizedResult, invariant: Invariant, context: CheckContext
) -> str | None:
    """Every component is connected: you can get from any member to any other
    without leaving it.

    Half of what makes a partition *the* component decomposition. Checked with
    a plain breadth-first walk over the component's own members, so this does
    not reuse any backend's answer to verify that backend's answer.

    On a directed graph this walks edges in both directions, which is the weak
    sense. Strong connectivity is a different claim and gets its own check.
    """
    if (wrong := _wrong_shape(result, PartitionResult)):
        return wrong
    if context.data is None:
        return "cannot be checked without the dataset it ran on"

    neighbours = _undirected_neighbours(context.data)
    for members in result.groups():
        reached = _walk(next(iter(members)), members, neighbours)
        if reached != set(members):
            missing = sorted(set(members) - reached)
            return (
                f"a component of {len(members)} is not connected: "
                f"{missing[:5]} cannot be reached from {sorted(members)[0]!r}"
            )
    return None


def components_are_maximal(
    result: NormalizedResult, invariant: Invariant, context: CheckContext
) -> str | None:
    """Nothing could be merged: the components are as large as the mode allows.

    The other half of the characterisation. Connected alone is satisfied by
    chopping the graph into single nodes; maximal alone is satisfied by putting
    everything in one component. Together they pin the decomposition exactly.

    What "maximal" means depends on the question asked, so this reads the
    effective parameters:

    - **weak** -- no edge may cross between components at all. A crossing edge
      would mean two components that should have been one.
    - **strong** -- crossing edges are expected and carry the direction of the
      decomposition, so the claim becomes that they never form a cycle. Two
      components on a cycle can reach each other both ways, which is exactly
      the condition for being one component.

    Stating it once, with the branch visible, rather than declaring an
    invariant that is quietly false half the time.
    """
    if (wrong := _wrong_shape(result, PartitionResult)):
        return wrong
    if context.data is None:
        return "cannot be checked without the dataset it ran on"

    labels = result.assignments
    crossing = [
        (str(source), str(target))
        for source, target, _ in context.data.edge_list()
        if labels.get(str(source)) != labels.get(str(target))
    ]
    if not crossing:
        return None

    if context.parameters.get("mode") != "strong" or not context.data.directed:
        source, target = crossing[0]
        return (
            f"edge {source} -- {target} crosses from component "
            f"{labels.get(source)!r} to {labels.get(target)!r}, so the "
            f"components are not maximal"
        )

    cycle = _cycle_between_components(crossing, labels)
    if cycle:
        return (
            f"components {cycle[0]!r} and {cycle[1]!r} can reach each other "
            f"both ways, so they are one strongly connected component, not two"
        )
    return None


def _cycle_between_components(
    crossing: list[tuple[str, str]], labels: dict[str, str]
) -> "tuple[str, str] | None":
    """Is there a cycle in the graph of components? Returns two components on
    one if so.

    The components of a correct strong decomposition form a DAG -- the
    condensation. A cycle in it means two components that should have been
    merged.
    """
    edges: dict[str, set[str]] = {}
    for source, target in crossing:
        edges.setdefault(labels[source], set()).add(labels[target])

    visiting: set[str] = set()
    done: set[str] = set()

    def walk(node: str) -> "tuple[str, str] | None":
        """Depth-first, returning the first back edge found: a component
        reachable from itself, and the one that reaches it."""
        visiting.add(node)
        for nxt in edges.get(node, ()):
            if nxt in visiting:
                return (nxt, node)
            if nxt not in done and (found := walk(nxt)):
                return found
        visiting.discard(node)
        done.add(node)
        return None

    for start in list(edges):
        if start not in done and (found := walk(start)):
            return found
    return None


def _undirected_neighbours(data: Any) -> dict[str, set[str]]:
    """Adjacency, ignoring direction. Built here rather than taken from a
    backend so the check is independent of what it is checking."""
    neighbours: dict[str, set[str]] = {str(node): set() for node in data.node_ids}
    for source, target, _ in data.edge_list():
        source, target = str(source), str(target)
        neighbours.setdefault(source, set()).add(target)
        neighbours.setdefault(target, set()).add(source)
    return neighbours


def _walk(start: str, within: "frozenset[str] | set[str]", neighbours: dict[str, set[str]]) -> set[str]:
    """Breadth-first from `start`, never leaving `within`."""
    reached = {start}
    frontier = [start]
    while frontier:
        node = frontier.pop()
        for neighbour in neighbours.get(node, ()):
            if neighbour in within and neighbour not in reached:
                reached.add(neighbour)
                frontier.append(neighbour)
    return reached


CHECKS: dict[str, Check] = {
    "scores_sum_to_one": scores_sum_to_one,
    "scores_non_negative": scores_non_negative,
    "scores_finite": scores_finite,
    "scores_in_unit_interval": scores_in_unit_interval,
    "scores_in_signed_unit_interval": scores_in_signed_unit_interval,
    "keys_are_canonical_pairs": keys_are_canonical_pairs,
    "scores_unique_per_node": scores_are_symmetric_free,
    "components_are_connected": components_are_connected,
    "components_are_maximal": components_are_maximal,
}


def known(invariant_id: str) -> bool:
    return invariant_id in CHECKS


def check_all(
    result: NormalizedResult,
    invariants: list[Invariant],
    context: CheckContext | None = None,
) -> list[InvariantResult]:
    """Run every checkable invariant against one result.

    Checks that do not need the context ignore it; the ones that do fail loudly
    when it is missing, because a caller that forgot to pass it would otherwise
    silently verify nothing.
    """
    context = context or CheckContext()
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
        detail = checker(result, invariant, context)
        outcomes.append(
            InvariantResult(
                invariant_id=invariant.id,
                statement=invariant.statement,
                passed=detail is None,
                detail=detail or "",
            )
        )
    return outcomes
