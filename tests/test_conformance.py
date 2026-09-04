"""The conformance suite: generated entirely from the registry.

A contributor who adds `methods/<id>/` gets all of these tests for free and
writes none of them. That is the point -- the barrier to contributing a method
should be the method, not the test harness.

Two independent questions, asked separately:

1. With every ambiguous parameter pinned, do the backends agree?
2. Does every divergence the registry declares still reproduce?
"""

from __future__ import annotations

import pytest

from conftest import executable_algorithms
from gigi import registry
from gigi.data import load_dataset
from gigi.harness import compare, runnable_backends, verify
from gigi.models import RunStatus

# Frontier entries are excluded unless opted in; see tests/conftest.py.
ALGORITHMS = executable_algorithms()


def _agreement_cases():
    for method_id in ALGORITHMS:
        spec = registry.load_method(method_id)
        backends = [e for e in runnable_backends(spec) if e != "reference"]
        for dataset_id in spec.datasets:
            for backend in backends:
                yield pytest.param(
                    method_id, dataset_id, backend, id=f"{method_id}-{dataset_id}-{backend}"
                )


def _divergence_cases():
    for method_id in ALGORITHMS:
        spec = registry.load_method(method_id)
        for divergence in spec.divergences:
            if divergence.detect:
                yield pytest.param(
                    method_id, divergence.id, id=f"{method_id}-{divergence.id}"
                )


@pytest.mark.parametrize("method_id,dataset_id,backend", list(_agreement_cases()))
def test_engine_agrees_with_reference(method_id, dataset_id, backend):
    """Under pinned parameters, every backend must match the reference -- unless
    the registry already declares why it cannot."""
    spec = registry.load_method(method_id)
    data = load_dataset(dataset_id)
    runs, comparisons = compare(spec, data, backends=["reference", backend], explicit=True)

    declared = [
        d.id
        for d in spec.divergences
        if d.detect and dataset_id in d.detect.datasets and backend in d.detect.backends
    ]

    subject = next(r for r in runs if r.backend == backend)
    if subject.status != RunStatus.ok:
        assert declared, (
            f"{backend} failed on {dataset_id} ({subject.error}) and no divergence "
            f"in method.yaml accounts for it"
        )
        return

    comparison = comparisons[0]
    assert comparison.equivalent or declared, (
        f"{backend} differs from reference on {dataset_id} "
        f"(max abs error {comparison.metrics.get('max_abs_error')}) and no "
        f"divergence in method.yaml accounts for it"
    )


@pytest.mark.parametrize("method_id,divergence_id", list(_divergence_cases()))
def test_declared_divergence_reproduces(method_id, divergence_id):
    """A divergence that no longer happens is stale documentation, and stale
    documentation is worse than none."""
    spec = registry.load_method(method_id)
    report = verify(spec)
    check = next(c for c in report.divergence_checks if c.divergence_id == divergence_id)

    if check.observed == "skipped":
        pytest.skip(check.note)
    assert check.reproduced, (
        f"{divergence_id}: registry expects {check.expected}, observed "
        f"{check.observed}. {check.note}"
    )


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_verification_passes(method_id):
    report = verify(registry.load_method(method_id))
    assert report.status == "pass", report.conclusion


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_effective_parameters_are_recorded(method_id):
    """A backend default that is not written down is a backend default nobody
    can audit."""
    spec = registry.load_method(method_id)
    dataset_id = spec.datasets[0]
    for backend in runnable_backends(spec):
        runs, _ = compare(spec, dataset_id, backends=[backend], explicit=True)
        result = runs[0]
        if result.status is RunStatus.ok:
            assert result.effective_parameters, f"{backend} reported no effective parameters"
