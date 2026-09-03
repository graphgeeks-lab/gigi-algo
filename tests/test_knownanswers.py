"""Known answers, checked -- against the reference first, then every engine.

Generated from `algorithms/<id>/tests/expected.yaml`. A contributor writes
cases in YAML; this file turns each into a test. Nothing here is specific to
any algorithm.
"""

from __future__ import annotations

import pytest

from gigi import knownanswers, registry
from gigi.harness import runnable_engines
from gigi.models import RunStatus

ALGORITHMS = registry.list_algorithms()


def _cases():
    for algorithm_id in ALGORITHMS:
        for case in knownanswers.load_cases(algorithm_id):
            yield pytest.param(algorithm_id, case, id=f"{algorithm_id}-{case.id}")


def _engine_cases():
    # Fixture-backed cases only. A declared divergence names a fixture and an
    # engine, so it can excuse exactly these; an inline graph has no id to
    # declare against. Inline cases therefore check the reference alone.
    for algorithm_id in ALGORITHMS:
        spec = registry.load_algorithm(algorithm_id)
        engines = [e for e in runnable_engines(spec) if e != "reference"]
        for case in knownanswers.load_cases(algorithm_id):
            if case.dataset is None:
                continue
            for engine in engines:
                yield pytest.param(
                    algorithm_id, case, engine, id=f"{algorithm_id}-{case.id}-{engine}"
                )


@pytest.mark.parametrize("algorithm_id,case", list(_cases()))
def test_reference_gives_the_known_answer(algorithm_id, case):
    """The oracle against something it did not produce."""
    result = knownanswers.run_case(algorithm_id, case, engine="reference")
    assert result.passed, f"{case.id} ({case.derived.strip()[:60]}...): {result.detail}"


@pytest.mark.parametrize("algorithm_id,case,engine", list(_engine_cases()))
def test_engines_give_the_known_answer_unless_excused(algorithm_id, case, engine):
    """Engines must match the hand-derived answer too, unless a declared
    divergence covers this engine on this fixture."""
    spec = registry.load_algorithm(algorithm_id)
    excused = case.dataset is not None and any(
        d.detect and case.dataset in d.detect.datasets and engine in d.detect.engines
        for d in spec.divergences
    )
    result = knownanswers.run_case(algorithm_id, case, engine=engine)
    if excused:
        return
    assert result.passed, f"{engine} on {case.id}: {result.detail}"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_every_case_says_where_its_answer_came_from(algorithm_id):
    """`derived` is the point of the file. A case derived by running the code
    checks the code against itself."""
    for case in knownanswers.load_cases(algorithm_id):
        text = case.derived.lower()
        assert len(case.derived.strip()) >= 12, f"{case.id}: derivation too short to mean anything"
        for phrase in ("ran the code", "ran it", "output of", "from running"):
            assert phrase not in text, f"{case.id}: derived from running the code -- that is circular"


def test_case_failure_is_reported_clearly():
    """When a case fails, the message names the node, both values and the gap."""
    from gigi.models import InlineGraph, KnownAnswer

    wrong = KnownAnswer(
        id="deliberately_wrong",
        derived="a value chosen to be wrong, for this test",
        graph=InlineGraph(directed=False, edges=[["a", "b"]]),
        parameters={"normalized": True},
        expected={"a": 0.25, "b": 1.0},
    )
    result = knownanswers.run_case("degree_centrality", wrong)
    assert not result.passed
    assert "a: expected 0.25" in result.detail and "off by" in result.detail


def test_missing_engine_is_a_failure_not_a_crash():
    from gigi.models import InlineGraph, KnownAnswer

    case = KnownAnswer(
        id="on_an_engine_that_is_not_there",
        derived="irrelevant; this case tests reporting",
        graph=InlineGraph(edges=[["a", "b"]]),
        expected={"a": 0.5},
    )
    result = knownanswers.run_case("degree_centrality", case, engine="no_such_engine")
    assert not result.passed
    assert "no_such_engine" in result.detail or "unknown engine" in result.detail
