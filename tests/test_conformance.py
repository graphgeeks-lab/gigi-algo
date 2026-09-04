"""The conformance suite: generated entirely from the registry.

A contributor who adds `algorithms/<id>/` gets all of these tests for free and
writes none of them. That is the point -- the barrier to contributing an
algorithm should be the algorithm, not the test harness.

Two independent questions, asked separately:

1. With every ambiguous parameter pinned, do the engines agree?
2. Does every divergence the registry declares still reproduce?
"""

from __future__ import annotations

import pytest

from conftest import executable_algorithms
from gigi import registry
from gigi.graph import load_graph
from gigi.harness import compare, runnable_engines, verify
from gigi.models import RunStatus

# Frontier entries are excluded unless opted in; see tests/conftest.py.
ALGORITHMS = executable_algorithms()


def _agreement_cases():
    for algorithm_id in ALGORITHMS:
        spec = registry.load_algorithm(algorithm_id)
        engines = [e for e in runnable_engines(spec) if e != "reference"]
        for dataset_id in spec.datasets:
            for engine in engines:
                yield pytest.param(
                    algorithm_id, dataset_id, engine, id=f"{algorithm_id}-{dataset_id}-{engine}"
                )


def _divergence_cases():
    for algorithm_id in ALGORITHMS:
        spec = registry.load_algorithm(algorithm_id)
        for divergence in spec.divergences:
            if divergence.detect:
                yield pytest.param(
                    algorithm_id, divergence.id, id=f"{algorithm_id}-{divergence.id}"
                )


@pytest.mark.parametrize("algorithm_id,dataset_id,engine", list(_agreement_cases()))
def test_engine_agrees_with_reference(algorithm_id, dataset_id, engine):
    """Under pinned parameters, every engine must match the reference -- unless
    the registry already declares why it cannot."""
    spec = registry.load_algorithm(algorithm_id)
    graph = load_graph(dataset_id)
    runs, comparisons = compare(spec, graph, engines=["reference", engine], explicit=True)

    declared = [
        d.id
        for d in spec.divergences
        if d.detect and dataset_id in d.detect.datasets and engine in d.detect.engines
    ]

    subject = next(r for r in runs if r.engine == engine)
    if subject.status != RunStatus.ok:
        assert declared, (
            f"{engine} failed on {dataset_id} ({subject.error}) and no divergence "
            f"in algorithm.yaml accounts for it"
        )
        return

    comparison = comparisons[0]
    assert comparison.equivalent or declared, (
        f"{engine} differs from reference on {dataset_id} "
        f"(max abs error {comparison.metrics.get('max_abs_error')}) and no "
        f"divergence in algorithm.yaml accounts for it"
    )


@pytest.mark.parametrize("algorithm_id,divergence_id", list(_divergence_cases()))
def test_declared_divergence_reproduces(algorithm_id, divergence_id):
    """A divergence that no longer happens is stale documentation, and stale
    documentation is worse than none."""
    spec = registry.load_algorithm(algorithm_id)
    report = verify(spec)
    check = next(c for c in report.divergence_checks if c.divergence_id == divergence_id)

    if check.observed == "skipped":
        pytest.skip(check.note)
    assert check.reproduced, (
        f"{divergence_id}: registry expects {check.expected}, observed "
        f"{check.observed}. {check.note}"
    )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_verification_passes(algorithm_id):
    report = verify(registry.load_algorithm(algorithm_id))
    assert report.status == "pass", report.conclusion


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_effective_parameters_are_recorded(algorithm_id):
    """An engine default that is not written down is an engine default nobody
    can audit."""
    spec = registry.load_algorithm(algorithm_id)
    dataset_id = spec.datasets[0]
    for engine in runnable_engines(spec):
        runs, _ = compare(spec, dataset_id, engines=[engine], explicit=True)
        result = runs[0]
        if result.status is RunStatus.ok:
            assert result.effective_parameters, f"{engine} reported no effective parameters"
