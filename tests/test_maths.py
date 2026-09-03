"""The maths block has to be real maths, and the invariants have to run.

`maths.md` is prose and prose cannot be checked. This block is the same content
in a form that can be, so these tests exist to make sure it stays that way: an
invariant that names no implementation, or a choice point pointing at a
divergence that does not exist, is a claim nobody can act on.
"""

from __future__ import annotations

import pytest

from gigi import invariants, registry
from gigi.graph import list_datasets
from gigi.harness import compare, runnable_engines

ALGORITHMS = registry.list_algorithms()


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_stable_algorithms_state_their_maths(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    if spec.maturity.value != "stable":
        return
    assert spec.maths.summary, f"{algorithm_id}: maths.summary is empty"
    assert spec.maths.definition, f"{algorithm_id}: no maths.definition"
    assert spec.maths.definition.statement.strip()


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_every_checkable_invariant_is_implemented(algorithm_id):
    """A property that names no check is a comment with extra steps."""
    spec = registry.load_algorithm(algorithm_id)
    for invariant in spec.maths.checkable():
        assert invariants.known(invariant.id), (
            f"{algorithm_id}: invariant {invariant.id!r} has no check in "
            f"gigi/invariants.py (known: {sorted(invariants.CHECKS)})"
        )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_stable_algorithms_check_something(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    if spec.maturity.value != "stable":
        return
    assert spec.maths.checkable(), (
        f"{algorithm_id} is stable but asserts no property of its own output"
    )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_invariants_hold_on_every_engine(algorithm_id):
    """The point of the whole exercise: the maths is asserted on every engine,
    on every fixture, not just believed."""
    spec = registry.load_algorithm(algorithm_id)
    engines = runnable_engines(spec)
    for dataset_id in spec.datasets:
        runs, _ = compare(spec, dataset_id, engines=engines, explicit=True)
        for result in runs:
            if result.result is None:
                continue
            assert result.invariants, (
                f"{result.engine} on {dataset_id}: no invariants were checked"
            )
            failures = [f"{i.invariant_id}: {i.detail}" for i in result.failed_invariants]
            assert not failures, f"{result.engine} on {dataset_id}: {failures}"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_choice_points_resolve(algorithm_id):
    """Where the definition is under-determined, any divergence or fixture it
    points at must exist -- otherwise the link rots silently."""
    spec = registry.load_algorithm(algorithm_id)
    known_datasets = set(list_datasets())
    declared = {d.id for d in spec.divergences}

    ids = [choice.id for choice in spec.maths.under_determined]
    assert len(ids) == len(set(ids)), f"{algorithm_id}: duplicate choice point ids"

    for choice in spec.maths.under_determined:
        assert choice.question.strip(), f"{choice.id}: no question"
        if choice.divergence:
            assert choice.divergence in declared, (
                f"{choice.id} points at divergence {choice.divergence!r}, "
                f"which this algorithm does not declare"
            )
        for dataset_id in choice.datasets:
            assert dataset_id in known_datasets, (
                f"{choice.id} points at unknown dataset {dataset_id!r}"
            )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_every_declared_divergence_has_a_choice_point(algorithm_id):
    """Engines do not differ at random. If they diverge, the definition left
    room for it, and that room should be named."""
    spec = registry.load_algorithm(algorithm_id)
    if spec.maturity.value != "stable":
        return
    covered = {c.divergence for c in spec.maths.under_determined if c.divergence}
    for divergence in spec.divergences:
        assert divergence.id in covered, (
            f"{algorithm_id}: divergence {divergence.id!r} has no matching entry "
            f"in maths.under_determined -- say which choice in the definition "
            f"the engines made differently"
        )


def test_unknown_invariant_id_is_reported_not_ignored():
    from gigi.models import Invariant, NodeScoreResult

    outcomes = invariants.check_all(
        NodeScoreResult(scores={"a": 1.0}),
        [Invariant(id="not_a_real_check", statement="...", check=True)],
    )
    assert outcomes[0].passed is False
    assert "no check implemented" in outcomes[0].detail


def test_checks_actually_catch_violations():
    from gigi.models import Invariant, NodeScoreResult

    broken = NodeScoreResult(scores={"a": 0.5, "b": -0.1})
    outcomes = invariants.check_all(
        broken,
        [
            Invariant(id="scores_sum_to_one", statement="sums to one"),
            Invariant(id="scores_non_negative", statement="non-negative"),
        ],
    )
    assert not outcomes[0].passed
    assert not outcomes[1].passed
    assert "negative" in outcomes[1].detail
