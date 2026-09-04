"""Normalisation and comparison, tested without touching a backend."""

from __future__ import annotations

import pytest

from gigi.models import OutputKind, ScoreResult
from gigi.results import NormalizationError, compare_scores, normalize_scores

NODES = ["a", "b", "c"]


def test_normalizes_id_keyed_mapping():
    result = normalize_scores({"a": 1.0, "b": 2.0, "c": 3.0}, NODES, OutputKind.node_score)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_normalizes_index_keyed_mapping():
    result = normalize_scores({0: 1.0, 1: 2.0, 2: 3.0}, NODES, OutputKind.node_score)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_normalizes_positional_sequence():
    result = normalize_scores([1.0, 2.0, 3.0], NODES, OutputKind.node_score)
    assert result.scores == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_rejects_partial_results():
    with pytest.raises(NormalizationError, match="no score"):
        normalize_scores({"a": 1.0}, NODES, OutputKind.node_score)


def test_rejects_wrong_length_sequence():
    with pytest.raises(NormalizationError, match="scores for"):
        normalize_scores([1.0, 2.0], NODES, OutputKind.node_score)


def _scores(**values):
    return ScoreResult(kind=OutputKind.node_score, scores=dict(values))


def test_noise_below_tolerance_is_equivalent():
    equivalent, metrics, _ = compare_scores(
        _scores(a=0.5, b=0.5), _scores(a=0.5 + 1e-9, b=0.5), 1e-6, 1e-5
    )
    assert equivalent
    assert metrics["max_abs_error"] == pytest.approx(1e-9)


def test_difference_above_tolerance_is_not_equivalent():
    equivalent, metrics, _ = compare_scores(
        _scores(a=0.5, b=0.5), _scores(a=0.6, b=0.4), 1e-6, 1e-5
    )
    assert not equivalent
    assert metrics["max_abs_error"] == pytest.approx(0.1)


def test_different_node_sets_are_never_equivalent():
    equivalent, _, notes = compare_scores(
        _scores(a=1.0), _scores(a=1.0, b=0.0), 1e-6, 1e-5
    )
    assert not equivalent
    assert "key sets differ" in notes[0]


def test_top_node_metric_is_reported():
    _, metrics, _ = compare_scores(
        _scores(a=0.9, b=0.1), _scores(a=0.1, b=0.9), 1e-6, 1e-5
    )
    assert metrics["top_key_agrees"] == 0.0


def test_nan_is_never_equivalent():
    """abs(x - nan) is nan, and nan > tolerance is False -- so without an explicit
    guard a NaN result passes every comparison. It did, once."""
    equivalent, metrics, notes = compare_scores(
        _scores(a=0.0), _scores(a=float("nan")), 1e-6, 1e-5
    )
    assert not equivalent
    assert any("non-finite" in n for n in notes)


def test_infinity_is_never_equivalent():
    equivalent, _, _ = compare_scores(
        _scores(a=1.0), _scores(a=float("inf")), 1e-6, 1e-5
    )
    assert not equivalent
