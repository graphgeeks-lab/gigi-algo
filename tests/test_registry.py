"""The registry has to be internally consistent before anything is run."""

from __future__ import annotations

import pytest

from gigi import registry
from gigi.adapters import ENGINES
from gigi.graph import list_datasets

ALGORITHMS = registry.list_algorithms()


def test_registry_is_not_empty():
    assert ALGORITHMS, "no algorithms found -- check GIGI_ALGORITHMS_DIR"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_spec_validates(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    assert spec.id == algorithm_id


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_declared_engines_have_implementations(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    for engine, support in spec.engines.items():
        assert engine in ENGINES, f"{engine} is not a known adapter"
        if support.supported:
            assert registry.has_implementation(algorithm_id, engine), (
                f"{algorithm_id} claims {engine} support but has no "
                f"implementations/{engine}.py"
            )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_implementations_have_declared_engines(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    for engine in registry.implemented_engines(algorithm_id):
        assert engine in spec.engines, (
            f"implementations/{engine}.py exists but algorithm.yaml does not "
            f"mention {engine}"
        )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_referenced_datasets_exist(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    known = set(list_datasets())
    assert spec.datasets, "an algorithm with no datasets cannot be verified"
    for dataset_id in spec.datasets:
        assert dataset_id in known, f"unknown dataset {dataset_id}"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_divergences_are_executable(algorithm_id):
    """A divergence without a detect block is an unverifiable claim. Stable
    algorithms are not allowed to make them."""
    spec = registry.load_algorithm(algorithm_id)
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
            assert len(divergence.detect.engines) == 2, "detect names baseline, then subject"
            for engine in divergence.detect.engines:
                assert engine in ENGINES
