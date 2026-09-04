"""The registry has to be internally consistent before anything is run."""

from __future__ import annotations

import pytest

from gigi import registry
from gigi.backends import BACKENDS
from gigi.data import list_datasets

ALGORITHMS = registry.list_methods()


def test_registry_is_not_empty():
    assert ALGORITHMS, "no algorithms found -- check GIGI_METHODS_DIR"


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_spec_validates(method_id):
    spec = registry.load_method(method_id)
    assert spec.id == method_id


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_declared_engines_have_implementations(method_id):
    spec = registry.load_method(method_id)
    for backend, support in spec.backends.items():
        assert backend in BACKENDS, f"{backend} is not a known adapter"
        if support.supported:
            assert registry.has_implementation(method_id, backend), (
                f"{method_id} claims {backend} support but has no "
                f"implementations/{backend}.py"
            )


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_implementations_have_declared_engines(method_id):
    spec = registry.load_method(method_id)
    for backend in registry.implemented_backends(method_id):
        assert backend in spec.backends, (
            f"implementations/{backend}.py exists but method.yaml does not "
            f"mention {backend}"
        )


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_referenced_datasets_exist(method_id):
    spec = registry.load_method(method_id)
    known = set(list_datasets())
    assert spec.datasets, "an algorithm with no datasets cannot be verified"
    for dataset_id in spec.datasets:
        assert dataset_id in known, f"unknown dataset {dataset_id}"


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_divergences_are_executable(method_id):
    """A divergence without a detect block is an unverifiable claim. Stable
    algorithms are not allowed to make them."""
    spec = registry.load_method(method_id)
    known_datasets = set(list_datasets())
    ids = [d.id for d in spec.divergences]
    assert len(ids) == len(set(ids)), "duplicate divergence ids"

    for divergence in spec.divergences:
        if spec.maturity.value == "stable":
            assert divergence.detect, (
                f"{divergence.id}: stable algorithms must make divergence "
                f"claims testable with a detect block"
            )
        if divergence.detect:
            assert divergence.detect.datasets, f"{divergence.id}: detect names no dataset"
            for dataset_id in divergence.detect.datasets:
                assert dataset_id in known_datasets, f"{divergence.id}: unknown dataset {dataset_id!r}"
            assert len(divergence.detect.backends) == 2, "detect names baseline, then subject"
            for backend in divergence.detect.backends:
                assert backend in BACKENDS
