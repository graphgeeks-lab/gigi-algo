"""Finding the registry entries a question is about.

The one piece of `gigi ask` that computes rather than formats. Everything else
in the ask path -- the CLI rendering, the agent tools, the MCP server -- is a
presentation of what this module and the existing harness already produce.

Deliberately not a search engine. No index, no embeddings, no ranking model:
token overlap against text the registry already carries for exactly this
purpose. `aliases`, `ai_context.synonyms` and a problem's `question` were
written to be matched against, and until now nothing read them.

The important output is not the best match. It is `answered_by` versus
`not_answered_by`: a question that maps to a problem no method solves should
say so, because "nothing here answers that" is a true and useful answer, and
the alternative is recommending something adjacent and wrong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gigi import registry

# Words that appear in almost every question and match almost every entry, so
# matching on them is noise. Short and hand-picked rather than a downloaded
# stopword list -- the vocabulary here is small enough to see.
NOISE = frozenset(
    """a an and are as at be by can do does for from get give
    has have how i in into is it me my of on or should show than that the
    their them there these this to use used using want was what when where
    which who why will with would you your""".split()
)


@dataclass(frozen=True)
class Match:
    """One registry entry a question might be about, and how well it fits."""

    kind: str  # "method" | "problem" | "family"
    id: str
    title: str
    score: float
    matched: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"{self.kind} {self.id} ({self.score:.2f})"


# A match has to clear both bars before it is allowed to recommend anything:
# a floor, so a single incidental word is not a match at all, and a share of
# the best score, so a strong hit is not diluted by weak ones.
#
# Both exist because the first version had neither. "the cheapest route between
# two cities" recommended cosine similarity, because the word *two* overlapped
# "how alike are these two things"; "how do I find communities" recommended
# connected components, which the registry explicitly says is the wrong answer.
# Weak matches may be shown as related. They may not answer.
RELEVANCE_FLOOR = 0.25
RELEVANCE_SHARE = 0.5


@dataclass
class Answer:
    """What the registry has to say about one question.

    `answered_by` and `not_answered_by` are the point. A method naming a problem
    in `intent.not_for` is claiming the question is a mistake to bring to it,
    and that claim is worth surfacing above any similarity score.
    """

    question: str
    matches: list[Match] = field(default_factory=list)
    confident: list[Match] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    answered_by: list[str] = field(default_factory=list)
    not_answered_by: list[tuple[str, str]] = field(default_factory=list)

    @property
    def found_nothing(self) -> bool:
        """Nothing cleared the floor. Weak matches may still be listed, but the
        honest headline is that the registry does not recognise the question."""
        return not self.confident

    @property
    def unanswered(self) -> bool:
        """A question the registry recognises but nothing solves. The most
        useful thing `ask` can report, and the easiest to paper over."""
        return bool(self.problems) and not self.answered_by


def tokens(text: str) -> set[str]:
    """Lowercase words worth matching on."""
    words = re.findall(r"[a-z0-9_]+", (text or "").lower())
    return {word for word in words if word not in NOISE and len(word) > 1}


def _score(question: str, asked: set[str], phrases: list[str], terms: list[str]) -> tuple[float, list[str]]:
    """How well one entry fits, and which of its terms did the fitting.

    A phrase the user typed nearly verbatim ("connected components") is much
    stronger evidence than sharing the word "components", so a phrase hit is
    worth more than the tokens it contains.
    """
    score = 0.0
    hits: list[str] = []

    lowered = question.lower()
    for phrase in phrases:
        cleaned = (phrase or "").strip().lower()
        if len(cleaned) > 2 and cleaned in lowered:
            score += 2.0 + 0.1 * len(cleaned.split())
            hits.append(phrase)

    for term in terms:
        overlap = tokens(term) & asked
        if overlap:
            score += len(overlap) / max(len(tokens(term)), 1)
            hits.extend(sorted(overlap))

    return score, hits


def _searchable():
    """Every entry worth matching, as (kind, id, title, phrases, terms).

    *Phrases* are things a user might type almost verbatim -- a name, an alias,
    a synonym -- and count for more. *Terms* are prose to overlap words against.
    Yielded from one place so the three kinds cannot drift into three different
    ideas of what is matchable.
    """
    for method_id in registry.list_methods():
        spec = registry.load_method(method_id)
        synonyms = spec.ai_context.synonyms if spec.ai_context else []
        yield (
            "method", method_id, spec.name,
            [spec.name, *spec.aliases, *synonyms],
            [method_id, spec.name, spec.summary],
        )

    for problem in registry.list_problems():
        synonyms = problem.ai_context.synonyms if problem.ai_context else []
        yield (
            "problem", problem.id, problem.name,
            [problem.name, *synonyms],
            [problem.id, problem.name, problem.question],
        )

    for family in registry.list_families():
        yield "family", family.id, family.name, [family.name], [family.id, family.question]


def search(question: str, limit: int = 6) -> list[Match]:
    """Registry entries this question is plausibly about, best first."""
    asked = tokens(question)
    if not asked:
        return []

    found: list[Match] = []
    for kind, entry_id, title, phrases, terms in _searchable():
        score, hits = _score(question, asked, phrases, terms)
        if score:
            found.append(Match(kind, entry_id, title, score, tuple(dict.fromkeys(hits))))

    found.sort(key=lambda m: (-m.score, m.kind, m.id))
    return found[:limit]


def ask(question: str, limit: int = 6) -> Answer:
    """Everything the registry has to say about one question.

    Problems are resolved to the methods that solve them *and* the methods that
    explicitly refuse them, because a question brought to the wrong method is
    the failure this whole registry exists to prevent.
    """
    answer = Answer(question=question, matches=search(question, limit))
    if not answer.matches:
        return answer

    threshold = max(RELEVANCE_FLOOR, answer.matches[0].score * RELEVANCE_SHARE)
    answer.confident = [m for m in answer.matches if m.score >= threshold]

    answer.problems = [m.id for m in answer.confident if m.kind == "problem"]
    # A matched method's own problems count too: asking "what does pagerank do"
    # should surface the question it answers, not only the method's name.
    for match in answer.confident:
        if match.kind == "method":
            answer.problems.extend(registry.load_method(match.id).problems)
    answer.problems = list(dict.fromkeys(answer.problems))

    refused: list[tuple[str, str]] = []
    for problem_id in answer.problems:
        answer.answered_by.extend(registry.methods_for_problem(problem_id))
        for method_id in registry.list_methods():
            if problem_id in registry.load_method(method_id).intent.not_for:
                refused.append((problem_id, method_id))
    answer.answered_by = list(dict.fromkeys(answer.answered_by))

    # A method that answers one of the matched problems is being recommended,
    # so listing it as out of scope for a *different* matched problem reads as
    # a contradiction rather than a warning. PageRank genuinely does not answer
    # "which nodes have the most connections" -- but saying so beside a
    # recommendation of PageRank helps nobody.
    answer.not_answered_by = [(p, m) for p, m in refused if m not in answer.answered_by]
    return answer
