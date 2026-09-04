"""The semantic layer: problems, roles, and the conflict check.

The check exists because the same column can be the right input to two methods
and mean opposite things to them. These tests pin the behaviour that makes it
trustworthy: it asks rather than rewrites, it stays quiet when the data matches
the method's assumption, and it says nothing at all when it has nothing to go
on.
"""

from __future__ import annotations

import pytest

from gigi import registry, semantics
from gigi.graph import load_graph
from gigi.models import DomainMeaning, SemanticInterpretation

METHODS = registry.list_methods()


# --- problems ---------------------------------------------------------------


@pytest.mark.parametrize("method_id", METHODS)
def test_every_problem_a_method_names_resolves(method_id):
    spec = registry.load_method(method_id)
    for problem_id in [*spec.problems, *spec.intent.not_for]:
        assert registry.problem_exists(problem_id), (
            f"{method_id} names problem {problem_id!r}, which is not in problems/"
        )


@pytest.mark.parametrize("problem_id", [p.id for p in registry.list_problems()])
def test_every_problem_is_referenced_by_some_method(problem_id):
    """A problem nobody solves and nobody is confused by is a note, not a
    registry entry. Being named in `not_for` counts: ruling a question out is
    as useful as answering it."""
    referenced = registry.methods_for_problem(problem_id) or [
        m for m in METHODS if problem_id in registry.load_method(m).intent.not_for
    ]
    assert referenced, f"problem {problem_id!r} is referenced by no method"


@pytest.mark.parametrize("problem_id", [p.id for p in registry.list_problems()])
def test_a_problem_is_a_question(problem_id):
    problem = registry.load_problem(problem_id)
    assert problem.question.strip().endswith("?")
    assert registry.domain_exists(problem.domain)
    for related in problem.related_problems:
        assert registry.problem_exists(related), f"{problem_id} -> unknown {related!r}"


@pytest.mark.parametrize("method_id", METHODS)
def test_a_method_does_not_claim_and_disclaim_the_same_problem(method_id):
    spec = registry.load_method(method_id)
    both = set(spec.problems) & set(spec.intent.not_for)
    assert not both, f"{method_id} both solves and does not solve {sorted(both)}"


# --- column meanings --------------------------------------------------------


@pytest.mark.parametrize(
    "column,expected",
    [
        ("distance", "distance"),
        ("DISTANCE", "distance"),
        ("travel_distance_km", "distance"),
        ("cost", "cost"),
        ("weight", "relationship_strength"),
        ("amount", "transaction_amount"),
        ("elapsed", "duration"),
    ],
)
def test_column_names_are_read_as_meanings(column, expected):
    assert semantics.infer_meaning(column) == expected


@pytest.mark.parametrize("column", ["w", "col3", "", "xyzzy", "predistance"])
def test_an_unrecognised_column_infers_nothing(column):
    """Silence is the correct output for a column we cannot read. A wrong guess
    costs more than no guess."""
    assert semantics.infer_meaning(column) is None


def test_the_vocabulary_is_data_not_code(monkeypatch, tmp_path):
    """Adding a hint is a one-line change to a YAML file."""
    path = tmp_path / "meanings.yaml"
    path.write_text("- meaning: temperature\n  hints: [celsius, kelvin]\n", encoding="utf-8")
    monkeypatch.setenv("GIGI_COLUMN_MEANINGS_FILE", str(path))
    semantics.vocabulary.cache_clear()
    try:
        assert semantics.infer_meaning("celsius") == "temperature"
        assert semantics.infer_meaning("distance") is None
    finally:
        semantics.vocabulary.cache_clear()


# --- the conflict check -----------------------------------------------------


def test_a_distance_column_read_as_strength_is_flagged():
    """The canonical case: same column, opposite meaning."""
    spec = registry.load_method("pagerank")
    findings = semantics.check_graph(spec, load_graph("road-distances-small"))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.serious
    assert finding.inferred_meaning == "distance"
    assert finding.semantic_role == "strength"
    assert "invert or transform" in finding.question().lower()


def test_a_column_that_matches_the_assumption_says_nothing():
    """`weight` reads as relationship strength, which is what PageRank assumes.
    A check that fires on the happy path gets ignored on the unhappy one."""
    spec = registry.load_method("pagerank")
    assert semantics.check_graph(spec, load_graph("weighted-small")) == []


def test_an_unweighted_graph_has_nothing_to_check():
    spec = registry.load_method("pagerank")
    assert semantics.check_graph(spec, load_graph("tiny-directed")) == []


def test_the_check_never_changes_anything():
    """It asks. Running the check must not alter the graph or the spec."""
    spec = registry.load_method("pagerank")
    graph = load_graph("road-distances-small")
    before_edges = graph.edge_list()
    before_params = [p.model_dump() for p in spec.parameters]

    semantics.check_graph(spec, graph)

    assert graph.edge_list() == before_edges
    assert [p.model_dump() for p in spec.parameters] == before_params


def test_an_unreadable_column_still_states_the_assumption():
    """A column we cannot read is not a silent pass: the method's assumption is
    stated anyway, as a question."""
    finding = semantics.Finding(
        column="w", inferred_meaning=None, subject="edge_weight",
        semantic_role="strength", higher_means="stronger", fit="unknown", note="",
    )
    assert not finding.serious
    assert "does not look like anything" in finding.question()
    assert "strength" in finding.question()


def test_a_meaning_the_method_never_mentions_is_surfaced_not_swallowed():
    """`distance` is readable, but if the method says nothing about distance we
    must not report that as agreement."""
    interpretation = SemanticInterpretation(
        id="x", subject="edge_weight", semantic_role="strength", higher_means="stronger",
        common_domain_meanings=[DomainMeaning(meaning="relationship_strength", fit="strong")],
    )
    spec = registry.load_method("pagerank").model_copy(
        update={"semantic_interpretations": [interpretation]}
    )
    findings = semantics.check_graph(spec, load_graph("road-distances-small"))

    assert len(findings) == 1
    assert findings[0].fit == "unknown"
    assert "does not say how it reads that" in findings[0].question()


# --- parameters carry their meaning -----------------------------------------


def test_pagerank_reads_weight_as_strength():
    parameter = registry.load_method("pagerank").parameter("weight_property")
    assert parameter.semantic_role == "strength"
    assert parameter.interpretation.higher_means == "stronger"


@pytest.mark.parametrize("method_id", METHODS)
def test_a_semantic_role_comes_with_an_interpretation(method_id):
    """`semantic_role: cost` alone does not say which direction is worse."""
    for parameter in registry.load_method(method_id).parameters:
        if parameter.semantic_role and parameter.semantic_role != "none":
            assert parameter.interpretation is not None, (
                f"{method_id}.{parameter.name} has a role but no interpretation"
            )


@pytest.mark.parametrize("method_id", METHODS)
def test_declared_meanings_are_from_the_known_vocabulary(method_id):
    """A method that warns about `distnace` warns about nothing."""
    known = {entry.meaning for entry in semantics.vocabulary()}
    for interpretation in registry.load_method(method_id).semantic_interpretations:
        for declared in interpretation.common_domain_meanings:
            assert declared.meaning in known, (
                f"{method_id}/{interpretation.id} names meaning {declared.meaning!r}, "
                f"which no column could ever be inferred as. Add it to "
                f"semantics/column_meanings.yaml or fix the spelling."
            )


@pytest.mark.parametrize("method_id", METHODS)
def test_a_dangerous_meaning_explains_itself(method_id):
    """Calling a reading dangerous without saying why is an alarm nobody acts on."""
    for interpretation in registry.load_method(method_id).semantic_interpretations:
        for declared in interpretation.common_domain_meanings:
            if declared.fit == "dangerous":
                assert declared.note and len(declared.note.strip()) > 20, (
                    f"{method_id}/{interpretation.id}: {declared.meaning} is flagged "
                    f"dangerous with no explanation"
                )


# --- use cases --------------------------------------------------------------


@pytest.mark.parametrize("method_id", METHODS)
def test_use_cases_map_their_inputs(method_id):
    for use_case in registry.load_method(method_id).use_cases:
        assert use_case.question.strip().endswith("?")
        assert use_case.input_mapping, (
            f"{method_id}/{use_case.id}: a use case without an input mapping is a "
            f"sentence, not a mapping onto the method"
        )
        for related in use_case.related_methods:
            assert registry.method_exists(related) or related not in METHODS
