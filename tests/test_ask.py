"""`gigi ask`, and the discipline that makes it worth having.

The retrieval itself is a few dozen lines of token overlap and not very
interesting. What is interesting is what it refuses to say: a registry whose
whole claim is that its contents are verified must not answer a question it
cannot ground, and must not offer the nearest method when the right answer is
"nothing here does that".

Every test below is about that boundary. The two named cases are real failures
from the first version, kept because they are the exact shape of the mistake.
"""

from __future__ import annotations

import pytest

from gigi import registry
from gigi.ask import RELEVANCE_FLOOR, Answer, ask, search, tokens


# --- the boundary -------------------------------------------------------------


def test_a_question_about_nothing_here_is_refused():
    """The registry knows graphs. Asked about something else, it must say so
    rather than reaching for whatever shares a word."""
    answer = ask("how do I train a neural network")
    assert answer.found_nothing
    assert not answer.answered_by


def test_a_known_question_nobody_answers_says_so():
    """`community_grouping` exists precisely so this can be answered honestly.
    Nothing here does community detection, and connected components is the
    thing people reach for by mistake."""
    answer = ask("how do I find communities in my graph")

    assert not answer.found_nothing, "the question is one the registry knows"
    assert answer.unanswered, "and nothing here answers it"
    assert "connected_components" not in answer.answered_by
    assert ("community_grouping", "connected_components") in answer.not_answered_by


def test_a_routing_question_is_not_answered_with_a_similarity_measure():
    """Regression. The first version scored `pairwise_vector_similarity` on the
    word *two* in "two cities" and recommended cosine similarity for a shortest
    path question. There is no shortest-path method here; the honest answer is
    that nothing answers it."""
    answer = ask("what is the cheapest route between two cities")

    assert "cosine_similarity" not in answer.answered_by
    assert answer.unanswered
    assert "cheapest_route" in answer.problems


@pytest.mark.parametrize(
    "question,expected",
    [
        ("which nodes are most important", {"degree_centrality", "pagerank"}),
        ("how similar are these two embeddings", {"cosine_similarity"}),
        ("is my graph connected", {"connected_components"}),
    ],
)
def test_questions_the_registry_can_answer(question, expected):
    assert set(ask(question).answered_by) == expected


# --- why the floor exists -----------------------------------------------------


def test_a_single_incidental_word_is_not_a_match():
    """"network" appears in prose all over the registry. Matching on it alone
    should not be enough to recommend anything."""
    answer = ask("my network is slow, how do I make it faster")
    assert not answer.answered_by


def test_weak_matches_are_kept_but_never_answer():
    """They are still worth showing as related -- they are just not allowed to
    drive a recommendation."""
    answer = ask("how do I find communities in my graph")
    weak = [m for m in answer.matches if m not in answer.confident]

    assert weak, "expected some weak matches to display"
    assert all(m.score < answer.confident[0].score for m in weak)


def test_the_floor_is_absolute_as_well_as_relative():
    """A lone weak match is still weak; being the best of a bad field must not
    promote it."""
    answer = ask("zzzz neural network")
    assert all(m.score < RELEVANCE_FLOOR for m in answer.matches) or answer.found_nothing


# --- no contradictions --------------------------------------------------------


def test_a_recommended_method_is_never_also_warned_against():
    """PageRank does not answer "which nodes have the most connections", but
    saying so beside a recommendation of PageRank reads as a contradiction."""
    answer = ask("which nodes are most important")
    warned = {method for _, method in answer.not_answered_by}

    assert warned.isdisjoint(answer.answered_by)


def test_every_id_it_returns_actually_resolves():
    """An answer naming something the registry does not have would be worse
    than no answer."""
    for question in ("important nodes", "similar vectors", "connected", "communities"):
        answer = ask(question)
        for method_id in answer.answered_by:
            assert registry.method_exists(method_id)
        for problem_id in answer.problems:
            assert registry.problem_exists(problem_id)
        for _, method_id in answer.not_answered_by:
            assert registry.method_exists(method_id)


# --- matching mechanics -------------------------------------------------------


def test_noise_words_are_dropped():
    assert tokens("how do I find the communities in my graph") == {
        "find",
        "communities",
        "graph",
    }


def test_an_empty_question_matches_nothing():
    for question in ("", "   ", "how do I"):
        assert search(question) == []
        assert ask(question).found_nothing


def test_a_phrase_beats_a_shared_word():
    """Typing a method's name nearly verbatim is much stronger evidence than
    sharing one word with its summary."""
    phrase = search("connected components")[0]
    assert phrase.id in {"connected_components", "component_membership"}
    assert phrase.score > 2.0


def test_aliases_are_matched():
    """`aliases:` was declared on every method and read by nothing until now.
    This is the test that keeps it honest."""
    assert any(m.id == "cosine_similarity" for m in search("angular similarity"))


def test_matches_are_ordered_and_capped():
    matches = search("graph nodes important connected similar", limit=3)
    assert len(matches) <= 3
    assert matches == sorted(matches, key=lambda m: (-m.score, m.kind, m.id))


def test_an_empty_answer_is_still_a_valid_answer():
    """Callers read the properties before the lists; they must not blow up on
    the empty case."""
    answer = Answer(question="x")
    assert answer.found_nothing
    assert not answer.unanswered
