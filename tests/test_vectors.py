"""The non-graph proof: a dataset, a backend and a result that are not graphs.

PR 1 made the *schema* stop being graph-shaped. These are the checks that the
*runtime* did too — that a backend can be handed something other than a graph,
that a result can be keyed by something other than a node, and that neither
needed a special case inside the harness.

The conformance suite already runs cosine similarity on three backends and
re-runs both its divergences; nothing here duplicates that. What is pinned here
is the machinery underneath, which no method-level test would notice breaking.
"""

from __future__ import annotations

import math

import pytest

from gigi import harness, registry
from gigi.backends.base import (
    ConvertedGraph,
    ConvertedVectors,
    UnsupportedInput,
    require_graph,
    require_vectors,
)
from gigi.data import load_dataset
from gigi.invariants import CHECKS, CheckContext
from gigi.models import Invariant, OutputKind, ScoreResult
from gigi.results import NormalizationError, compare_scores, normalize_scores
from gigi.vectors import PAIR_SEPARATOR, pair_key, vectors_from_rows

VECTORS = vectors_from_rows("test", {"b": [1.0, 0.0], "a": [0.0, 1.0]})


# --- pair keys ----------------------------------------------------------------


def test_a_pair_key_does_not_depend_on_the_order_it_was_asked_in():
    """The measure is symmetric, so the key must be too, or the same answer
    lands under two names and nothing can join on it."""
    assert pair_key("a", "b") == pair_key("b", "a") == f"a{PAIR_SEPARATOR}b"


def test_pair_keys_cover_every_unordered_pair_exactly_once():
    converted = ConvertedVectors(native=None, ids=["c", "a", "b"], dimensions=2)
    keys = converted.result_keys

    assert len(keys) == 3
    assert len(set(keys)) == 3
    assert set(keys) == {"a|c", "a|b", "b|c"}
    for key in keys:
        assert key.split(PAIR_SEPARATOR) == sorted(key.split(PAIR_SEPARATOR))


def test_one_vector_has_no_pairs():
    """The degenerate case for a pairwise measure, and the reason
    `vectors-single` is a fixture: the right answer is nothing at all."""
    assert ConvertedVectors(native=None, ids=["only"], dimensions=2).result_keys == []


# --- what a result is keyed by ------------------------------------------------


def test_a_graph_owes_a_score_for_every_node():
    converted = ConvertedGraph(
        native=None, node_ids=["a", "b"], directed=True, has_weights=False
    )
    assert converted.result_keys == ["a", "b"]
    assert converted.keys_are_complete


def test_a_pairwise_measure_may_decline_a_pair():
    """A zero vector has no direction, so some pairs genuinely have no answer.
    That is a finding for the comparator, not an error during normalisation."""
    converted = ConvertedVectors(native=None, ids=["a", "b"], dimensions=2)
    assert not converted.keys_are_complete


def test_a_missing_key_is_an_error_when_every_key_is_owed():
    with pytest.raises(NormalizationError, match="no score for"):
        normalize_scores({"a": 1.0}, ["a", "b"], OutputKind.node_score)


def test_a_missing_key_is_allowed_when_it_is_not():
    result = normalize_scores(
        {"a|b": 1.0}, ["a|b", "a|c", "b|c"], OutputKind.similarity_score,
        require_all_keys=False,
    )
    assert result.scores == {"a|b": 1.0}
    assert result.kind is OutputKind.similarity_score


def test_a_result_carries_the_kind_it_was_asked_for():
    """The comparator dispatches on it, so a result that does not know what it
    is cannot be judged."""
    result = normalize_scores([0.5], ["a|b"], OutputKind.similarity_score)
    assert result.kind is OutputKind.similarity_score


# --- backends refuse input they do not speak ----------------------------------


def test_a_graph_backend_refuses_vectors_by_name():
    with pytest.raises(UnsupportedInput, match="networkx takes a graph"):
        require_graph("networkx", VECTORS)


def test_a_vector_backend_refuses_a_graph_by_name():
    graph = load_dataset("tiny-directed")
    with pytest.raises(UnsupportedInput, match="scipy takes vectors"):
        require_vectors("scipy", graph)


def test_the_reference_backend_takes_both():
    """It is the oracle for every method, so it is the one backend that cannot
    be allowed to specialise."""
    from gigi.backends import reference

    assert isinstance(reference.convert(VECTORS), ConvertedVectors)
    assert isinstance(reference.convert(load_dataset("tiny-directed")), ConvertedGraph)


def test_wrong_input_is_a_failed_run_not_an_exception():
    """The harness contract: a backend failure is a RunResult with a status, so
    verification can report what did not run alongside what did."""
    result = harness.run("pagerank", "networkx", "vectors-small")
    assert result.status.value == "error"
    assert "takes a graph" in result.error


# --- the comparator, on keys that are not nodes -------------------------------


def test_two_backends_that_decline_different_pairs_are_not_equivalent():
    """The zero-vector case, reduced. scikit-learn answers 0.0 where the
    reference declines; that is a disagreement about whether the pair has an
    answer at all, and it must not read as agreement."""
    declined = ScoreResult(kind=OutputKind.similarity_score, scores={"p|r": 0.0})
    answered = ScoreResult(
        kind=OutputKind.similarity_score, scores={"p|q": 0.0, "p|r": 0.0, "q|r": 0.0}
    )
    equivalent, _, notes = compare_scores(declined, answered, 1e-12, 1e-12)

    assert not equivalent
    assert "key sets differ" in notes[0]


def test_the_reference_declines_exactly_the_undefined_pairs():
    """Measured, not asserted in prose: on `vectors-with-zero` the two pairs
    touching the zero vector have no answer and the third does."""
    result = harness.run("cosine_similarity", "reference", "vectors-with-zero")
    assert set(result.result.scores) == {"p|r"}


# --- invariants a pairwise measure can assert ---------------------------------


def _check(invariant_id, scores):
    return CHECKS[invariant_id](
        ScoreResult(kind=OutputKind.similarity_score, scores=scores),
        Invariant(id=invariant_id, statement="..."),
        CheckContext(),
    )


def test_cauchy_schwarz_is_checked_not_assumed():
    assert _check("scores_in_signed_unit_interval", {"a|b": -1.0, "a|c": 1.0}) is None
    assert "outside [-1, 1]" in _check("scores_in_signed_unit_interval", {"a|b": 1.5})


def test_a_negative_score_is_fine_here_and_not_elsewhere():
    """Cosine reaches -1 legitimately; a centrality does not. Two bounds, two
    checks, rather than one check that quietly widened."""
    assert _check("scores_in_signed_unit_interval", {"a|b": -1.0}) is None
    assert _check("scores_non_negative", {"a|b": -1.0}) is not None


def test_a_non_canonical_key_is_caught():
    assert _check("keys_are_canonical_pairs", {"a|b": 1.0}) is None
    assert "not canonical" in _check("keys_are_canonical_pairs", {"b|a": 1.0})
    assert "not canonical" in _check("keys_are_canonical_pairs", {"ab": 1.0})


def test_the_measure_is_scale_invariant():
    """The property people are choosing when they choose this measure, run
    rather than stated: doubling a vector must not move its score."""
    plain = harness.run(
        "cosine_similarity", "reference", vectors_from_rows("x", {"a": [1.0, 2.0], "b": [3.0, 1.0]})
    )
    scaled = harness.run(
        "cosine_similarity", "reference", vectors_from_rows("x", {"a": [7.0, 14.0], "b": [3.0, 1.0]})
    )
    assert math.isclose(plain.result.scores["a|b"], scaled.result.scores["a|b"], abs_tol=1e-12)


def test_a_vectors_run_records_a_vector_profile():
    """`RunResult.profile` stopped being a graph profile, and something has to
    notice if it quietly becomes one again."""
    result = harness.run("cosine_similarity", "reference", "vectors-small")
    assert result.profile.kind == "vectors"
    assert result.profile.vector_count == 4


def test_a_method_that_is_not_in_the_graph_domain_exists_at_all():
    spec = registry.load_method("cosine_similarity")
    assert registry.domain_of(spec) == "similarity"
    assert [i.kind for i in spec.inputs] == ["vectors"]


# --- the registry's picture of the backends matches the backends ---------------


@pytest.mark.parametrize("backend", sorted(registry.BACKEND_INPUT_KINDS))
def test_a_backend_accepts_exactly_the_kinds_the_registry_claims(backend):
    """`BACKEND_INPUT_KINDS` decides what a review calls a missing
    implementation, so a wrong entry there is a gap list telling contributors to
    write something impossible. One mapping, checked against the adapters that
    have to honour it."""
    from gigi.backends import get_backend

    module = get_backend(backend)
    claimed = set(registry.BACKEND_INPUT_KINDS[backend])
    samples = {"graph": load_dataset("tiny-directed"), "vectors": VECTORS}

    for kind, data in samples.items():
        if kind not in claimed:
            # Refusal happens before the library is imported, so this half holds
            # even where the backend is not installed.
            with pytest.raises(UnsupportedInput):
                module.convert(data)
        elif module.available():
            assert module.convert(data) is not None
