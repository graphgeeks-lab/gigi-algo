"""Known answers, checked -- against the reference first, then every backend.

Generated from `algorithms/<id>/tests/expected.yaml`. A contributor writes
cases in YAML; this file turns each into a test. Nothing here is specific to
any algorithm.
"""

from __future__ import annotations

import pytest

from conftest import executable_algorithms
from gigi import knownanswers, registry
from gigi.harness import runnable_backends

# Frontier entries are excluded unless opted in; see tests/conftest.py.
ALGORITHMS = executable_algorithms()


def _cases():
    for method_id in ALGORITHMS:
        for case in knownanswers.load_cases(method_id):
            yield pytest.param(method_id, case, id=f"{method_id}-{case.id}")


def _engine_cases():
    # Fixture-backed cases only. A declared divergence names a fixture and an
    # backend, so it can excuse exactly these; an inline graph has no id to
    # declare against. Inline cases therefore check the reference alone.
    for method_id in ALGORITHMS:
        spec = registry.load_method(method_id)
        backends = [e for e in runnable_backends(spec) if e != "reference"]
        for case in knownanswers.load_cases(method_id):
            if case.dataset is None:
                continue
            for backend in backends:
                yield pytest.param(
                    method_id, case, backend, id=f"{method_id}-{case.id}-{backend}"
                )


@pytest.mark.parametrize("method_id,case", list(_cases()))
def test_reference_gives_the_known_answer(method_id, case):
    """The oracle against something it did not produce."""
    result = knownanswers.run_case(method_id, case, backend="reference")
    assert result.passed, f"{case.id} ({case.derived.strip()[:60]}...): {result.detail}"


@pytest.mark.parametrize("method_id,case,backend", list(_engine_cases()))
def test_engines_give_the_known_answer_unless_excused(method_id, case, backend):
    """Backends must match the hand-derived answer too, unless a declared
    divergence covers this backend on this fixture."""
    spec = registry.load_method(method_id)
    excused = case.dataset is not None and any(
        d.detect and case.dataset in d.detect.datasets and backend in d.detect.backends
        for d in spec.divergences
    )
    result = knownanswers.run_case(method_id, case, backend=backend)
    if excused:
        return
    assert result.passed, f"{backend} on {case.id}: {result.detail}"


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_every_case_says_where_its_answer_came_from(method_id):
    """`derived` is the point of the file. A case derived by running the code
    checks the code against itself."""
    for case in knownanswers.load_cases(method_id):
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
    result = knownanswers.run_case("degree_centrality", case, backend="no_such_engine")
    assert not result.passed
    assert "no_such_engine" in result.detail or "unknown backend" in result.detail
