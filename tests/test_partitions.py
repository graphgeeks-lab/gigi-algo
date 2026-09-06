"""A result that is a grouping, not a number per key.

`node_score` and `similarity_score` are one number per key and share a
comparator. `partition` is the first output kind that could not, and these are
the checks on the machinery that makes it work: a normaliser that takes four
backend shapes, a comparator that ignores what components are called, and
invariants that can see the graph and the question.

The conformance suite already runs `connected_components` on four backends
across eleven fixtures. Nothing here duplicates that; this is the layer beneath,
which no method-level test would notice breaking.
"""

from __future__ import annotations

import pytest

from gigi import harness, registry
from gigi.data import load_dataset
from gigi.invariants import CHECKS, CheckContext
from gigi.models import Invariant, OutputKind, PartitionResult, RunResult, ScoreResult
from gigi.results import NormalizationError, compare_partitions, normalize_partition

KEYS = ["a", "b", "c"]

# The four shapes the real backends return, all meaning {a,b} and {c}. Taken
# from what they actually returned, not from their documentation.
SHAPES = {
    "reference": [{"a", "b"}, {"c"}],
    "networkx": [{"b", "a"}, {"c"}],
    "igraph": [0, 0, 1],
    "igraph-labelled-backwards": [1, 1, 0],
    "rustworkx": [{0, 1}, {2}],
    "mapping": {"a": "x", "b": "x", "c": "y"},
}


# --- normalisation ------------------------------------------------------------


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_every_backend_shape_normalises_to_the_same_thing(shape):
    """The point of the normaliser. Four libraries, four conventions, one
    result -- otherwise the comparator would be comparing return types."""
    assert normalize_partition(SHAPES[shape], KEYS).assignments == {
        "a": "c0",
        "b": "c0",
        "c": "c1",
    }


def test_labels_are_canonical_not_whatever_the_backend_said():
    """igraph labels the same partition `[1, 1, 0]` here and `[0, 0, 1]`
    elsewhere depending on traversal order. Neither is wrong and neither is the
    answer, so both are rewritten."""
    forwards = normalize_partition([0, 0, 1], KEYS)
    backwards = normalize_partition([1, 1, 0], KEYS)
    assert forwards.assignments == backwards.assignments


def test_a_key_in_two_components_is_refused():
    """A partition whose parts overlap is not a partition."""
    with pytest.raises(NormalizationError, match="cannot overlap"):
        normalize_partition([{"a", "b"}, {"b", "c"}], KEYS)


def test_a_key_that_was_never_in_the_graph_is_refused():
    with pytest.raises(NormalizationError, match="unknown key"):
        normalize_partition([{"a", "b"}, {"zzz"}], KEYS)


def test_every_node_must_be_placed():
    """A node dropped from every component is the classic bug in an
    implementation that walks edges instead of nodes."""
    with pytest.raises(NormalizationError, match="no component"):
        normalize_partition([{"a", "b"}], KEYS)


def test_a_membership_vector_of_the_wrong_length_is_refused():
    with pytest.raises(NormalizationError, match="membership vector"):
        normalize_partition([0, 0], KEYS)


def test_an_index_out_of_range_says_so():
    with pytest.raises(NormalizationError, match="index 9"):
        normalize_partition([{0, 9}, {2}], KEYS)


def test_an_empty_graph_gives_an_empty_partition():
    assert normalize_partition([], []).assignments == {}


# --- the partition itself -----------------------------------------------------


def test_groups_are_the_mathematical_object():
    result = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    assert result.groups() == frozenset({frozenset({"a", "b"}), frozenset({"c"})})
    assert result.component_count == 2
    assert result.sizes() == [2, 1]


def test_a_partition_result_cannot_claim_to_be_a_score():
    """The union in RunResult discriminates on `kind`, so a result that lied
    about its kind would be judged by the wrong comparator."""
    with pytest.raises(Exception):
        ScoreResult(kind=OutputKind.partition, scores={})


def test_a_stored_partition_comes_back_a_partition():
    """Runs are saved as JSON and read back; a union that round-tripped into
    the wrong class would be a silent corruption."""
    result = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    stored = RunResult(run_id="x", method_id="m", backend="b", result=result)
    restored = RunResult.model_validate_json(stored.model_dump_json())

    assert isinstance(restored.result, PartitionResult)
    assert restored.result.groups() == result.groups()


# --- comparison ---------------------------------------------------------------


def test_the_same_grouping_under_different_labels_is_the_same_answer():
    a = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    b = normalize_partition([1, 1, 0], KEYS)
    equivalent, metrics, notes = compare_partitions(a, b, 0.0, 0.0)

    assert equivalent
    assert not notes
    assert metrics["keys_grouped_differently"] == 0.0


def test_a_genuinely_different_grouping_is_caught():
    together = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    apart = normalize_partition([{"a"}, {"b"}, {"c"}], KEYS)
    equivalent, metrics, notes = compare_partitions(together, apart, 0.0, 0.0)

    assert not equivalent
    assert metrics["keys_grouped_differently"] == 2.0
    assert "grouped differently" in notes[0]


def test_tolerance_cannot_make_two_partitions_nearly_equal():
    """There is no such thing as approximately the same grouping, and a
    generous tolerance must not be able to pretend otherwise."""
    together = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    apart = normalize_partition([{"a"}, {"b"}, {"c"}], KEYS)
    assert not compare_partitions(together, apart, 1e9, 1e9)[0]


def test_different_key_sets_are_reported_as_such():
    a = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    b = normalize_partition([{"a", "b"}], ["a", "b"])
    equivalent, _, notes = compare_partitions(a, b, 0.0, 0.0)

    assert not equivalent
    assert "key sets differ" in notes[0]


# --- invariants that need the graph and the question --------------------------


def _check(invariant_id, result, **context):
    return CHECKS[invariant_id](result, Invariant(id=invariant_id, statement="..."), CheckContext(**context))


def test_connectivity_is_checked_against_the_graph_not_the_backend():
    graph = load_dataset("disconnected-small")
    lumped = PartitionResult(assignments={n: "c0" for n in graph.node_ids})

    detail = _check("components_are_connected", lumped, data=graph)
    assert detail and "not connected" in detail


def test_maximality_catches_a_partition_that_is_too_fine():
    """Connectivity alone is satisfied by chopping the graph into single nodes.
    This is the check that stops that passing."""
    graph = load_dataset("disconnected-small")
    shredded = PartitionResult(assignments={n: f"c{i}" for i, n in enumerate(graph.node_ids)})

    assert _check("components_are_connected", shredded, data=graph) is None
    assert "not maximal" in _check("components_are_maximal", shredded, data=graph)


def test_maximality_means_something_different_under_strong():
    """A crossing edge is a bug under `weak` and expected under `strong`. An
    invariant that ignored the question would be false half the time."""
    graph = load_dataset("two-clusters-directed")
    strong = harness.run("connected_components", "reference", graph, parameters={"mode": "strong"})

    # Crossing edges exist here: b -> c joins the two strong components.
    assert "not maximal" in _check("components_are_maximal", strong.result, data=graph)
    assert (
        _check("components_are_maximal", strong.result, data=graph, parameters={"mode": "strong"})
        is None
    )


def test_strong_maximality_still_catches_a_real_error():
    """Under `strong` the claim weakens to "the condensation is acyclic", and
    it has to stay strong enough to fail on something."""
    graph = load_dataset("two-clusters-directed")
    shredded = PartitionResult(assignments={n: f"c{i}" for i, n in enumerate(graph.node_ids)})

    detail = _check("components_are_maximal", shredded, data=graph, parameters={"mode": "strong"})
    assert detail and "both ways" in detail


def test_a_check_without_its_dataset_fails_rather_than_passing():
    """A caller that forgot the context must not get a green tick."""
    result = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    assert "cannot be checked" in _check("components_are_connected", result)


def test_a_score_invariant_named_on_a_partition_says_so():
    """An authoring mistake in method.yaml, surfaced as a failed invariant
    rather than an AttributeError from inside a check."""
    result = normalize_partition([{"a", "b"}, {"c"}], KEYS)
    detail = _check("scores_sum_to_one", result)
    assert detail and "ScoreResult" in detail and "PartitionResult" in detail


# --- the method, end to end ---------------------------------------------------


def test_mode_actually_changes_the_answer():
    """If weak and strong gave the same answer everywhere, `mode` would be
    decoration and the choice point would be a fiction."""
    weak = harness.run("connected_components", "reference", "two-clusters-directed",
                       parameters={"mode": "weak"})
    strong = harness.run("connected_components", "reference", "two-clusters-directed",
                         parameters={"mode": "strong"})

    assert weak.result.component_count == 1
    assert strong.result.component_count == 2


def test_the_strong_decomposition_refines_the_weak_one():
    """A structural fact from method.yaml, executed: every strong component sits
    inside one weak component, so there are never fewer strong than weak."""
    for dataset_id in registry.load_method("connected_components").datasets:
        data = load_dataset(dataset_id)
        if not data.directed:
            continue
        weak = harness.run("connected_components", "reference", data, parameters={"mode": "weak"})
        strong = harness.run("connected_components", "reference", data, parameters={"mode": "strong"})

        assert strong.result.component_count >= weak.result.component_count, dataset_id
        for group in strong.result.groups():
            containing = {weak.result.assignments[key] for key in group}
            assert len(containing) == 1, (
                f"{dataset_id}: strong component {sorted(group)} spans weak "
                f"components {sorted(containing)}"
            )


def test_an_isolated_node_is_its_own_component():
    """`disconnected-small` has n6 with no edges. An implementation that builds
    components by walking edges loses it silently."""
    result = harness.run("connected_components", "reference", "disconnected-small")
    assert result.result.assignments["n6"] not in {
        result.result.assignments[n] for n in ("n1", "n2", "n3", "n4", "n5")
    }
