"""Normalisation and comparison, tested without touching an engine."""

from __future__ import annotations

import pytest

from gigi.models import NodeScoreResult
from gigi.results import NormalizationError, compare_node_scores, normalize_node_score

NODES = ["a", "b", "c"]


def test_normalizes_id_keyed_mapping():
    result = normalize_node_score({"a": 1.0, "b": 2.0, "c": 3.0}, NODES)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_normalizes_index_keyed_mapping():
    result = normalize_node_score({0: 1.0, 1: 2.0, 2: 3.0}, NODES)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_normalizes_positional_sequence():
    result = normalize_node_score([1.0, 2.0, 3.0], NODES)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_rejects_partial_results():
    with pytest.raises(NormalizationError, match="no score"):
        normalize_node_score({"a": 1.0}, NODES)


def test_rejects_wrong_length_sequence():
    with pytest.raises(NormalizationError, match="scores for"):
        normalize_node_score([1.0, 2.0], NODES)


def _scores(**values):
    return NodeScoreResult(scores=dict(values))


def test_noise_below_tolerance_is_equivalent():
    equivalent, metrics, _ = compare_node_scores(
        _scores(a=0.5, b=0.5), _scores(a=0.5 + 1e-9, b=0.5), 1e-6, 1e-5
    )
    assert equivalent
    assert metrics["max_abs_error"] == pytest.approx(1e-9)


def test_difference_above_tolerance_is_not_equivalent():
    equivalent, metrics, _ = compare_node_scores(
        _scores(a=0.5, b=0.5), _scores(a=0.6, b=0.4), 1e-6, 1e-5
    )
    assert not equivalent
    assert metrics["max_abs_error"] == pytest.approx(0.1)


def test_different_node_sets_are_never_equivalent():
    equivalent, _, notes = compare_node_scores(
        _scores(a=1.0), _scores(a=1.0, b=0.0), 1e-6, 1e-5
    )
    assert not equivalent
    assert "node sets differ" in notes[0]


def test_top_node_metric_is_reported():
    _, metrics, _ = compare_node_scores(
        _scores(a=0.9, b=0.1), _scores(a=0.1, b=0.9), 1e-6, 1e-5
    )
    assert metrics["top_node_agrees"] == 0.0
