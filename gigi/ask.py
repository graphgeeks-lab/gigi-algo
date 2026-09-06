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

import json
import re
from dataclasses import dataclass, field
from typing import Sequence

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
    # Which path found the matches: "keywords", or the provider's name. Shown
    # to the user, because whether a model was involved in choosing is
    # something they are entitled to know without asking.
    matched_by: str = "keywords"
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


def _score(question: str, asked: set[str], phrases: list[str], terms: list[str]) -> float:
    """How well one entry fits the question.

    A phrase the user typed nearly verbatim ("connected components") is much
    stronger evidence than sharing the word "components", so a phrase hit is
    worth more than the tokens it contains.
    """
    score = 0.0
    lowered = question.lower()

    for phrase in phrases:
        cleaned = (phrase or "").strip().lower()
        if len(cleaned) > 2 and cleaned in lowered:
            score += 2.0 + 0.1 * len(cleaned.split())

    for term in terms:
        overlap = tokens(term) & asked
        if overlap:
            score += len(overlap) / max(len(tokens(term)), 1)

    return score


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

    found = [
        Match(kind, entry_id, title, score)
        for kind, entry_id, title, phrases, terms in _searchable()
        if (score := _score(question, asked, phrases, terms))
    ]

    found.sort(key=lambda m: (-m.score, m.kind, m.id))
    return found[:limit]


def ask(question: str, limit: int = 6, provider=None) -> Answer:
    """Everything the registry has to say about one question.

    Problems are resolved to the methods that solve them *and* the methods that
    explicitly refuse them, because a question brought to the wrong method is
    the failure this whole registry exists to prevent.

    With a `provider`, a model chooses which entries the question is about --
    it reads paraphrase, which token overlap cannot. It selects ids and nothing
    else; every one is validated, and everything below this line is identical
    either way. If it returns nothing usable, keyword matching runs instead, so
    the answer degrades rather than disappearing.
    """
    matched_by = "keywords"
    matches: list[Match] = []

    if provider is not None:
        matches = search_with_model(question, provider, limit)
        if matches:
            matched_by = getattr(provider, "NAME", "model")

    if not matches:
        matches = search(question, limit)

    answer = Answer(question=question, matched_by=matched_by, matches=matches)
    if not answer.matches:
        return answer

    threshold = max(RELEVANCE_FLOOR, answer.matches[0].score * RELEVANCE_SHARE)
    answer.confident = [m for m in answer.matches if m.score >= threshold]

    # The questions the user actually asked, before any method gets a say.
    answer.problems = [m.id for m in answer.confident if m.kind == "problem"]

    # The best reading of the question. When nothing in the registry answers
    # it, no method that has declared itself the wrong answer to it may be
    # offered instead -- that substitution is the exact failure this whole
    # registry exists to prevent, and it is what a matcher does by default.
    #
    #   "how do I find communities"  -> community_grouping, which nothing
    #       answers. connected_components declares it out of scope, and also
    #       answers component_membership, which a matcher reasonably offers as
    #       a second reading. Without this it answers via the back door.
    #
    # The condition is narrow on purpose. When the top question *is* answered,
    # a disclaimer means only "not this particular problem", and the method may
    # still answer a different one:
    #
    #   "which nodes are most important" -> simple_node_importance (answered by
    #       degree_centrality) and recursive_node_influence (answered by
    #       PageRank). PageRank disclaims the first and answers the second.
    #       Both are correct answers to an ambiguous question, and both are
    #       shown.
    top_question = answer.problems[0] if answer.problems else None
    refused: set[str] = set()
    if top_question and not registry.methods_for_problem(top_question):
        refused = {
            method_id
            for method_id in registry.list_methods()
            if top_question in registry.load_method(method_id).intent.not_for
        }

    # A matched method's own problems count too: asking "what does pagerank do"
    # should surface the question it answers, not only the method's name.
    for match in answer.confident:
        if match.kind == "method" and match.id not in refused:
            answer.problems.extend(registry.load_method(match.id).problems)
    answer.problems = list(dict.fromkeys(answer.problems))

    warned: list[tuple[str, str]] = []
    for problem_id in answer.problems:
        answer.answered_by.extend(
            m for m in registry.methods_for_problem(problem_id) if m not in refused
        )
        for method_id in registry.list_methods():
            if problem_id in registry.load_method(method_id).intent.not_for:
                warned.append((problem_id, method_id))
    answer.answered_by = list(dict.fromkeys(answer.answered_by))

    # A method that answers one of the matched problems is being recommended,
    # so listing it as out of scope for a *different* matched problem reads as
    # a contradiction rather than a warning.
    answer.not_answered_by = [(p, m) for p, m in warned if m not in answer.answered_by]
    return answer


# --- matching with a model ----------------------------------------------------
#
# Token overlap misses paraphrase, and paraphrase is how people actually ask.
# "which nodes matter most" shares no word with "important", so keyword matching
# returns degree centrality and silently drops PageRank.
#
# A model fixes that, and is allowed to do exactly one thing: choose ids from a
# catalogue the registry supplies. It is never asked what a method does, and
# nothing it writes reaches the user. Every id it returns is resolved against
# the registry and dropped if it does not exist, so the failure mode of a bad
# model is *matching nothing*, not asserting something false.
#
# See docs/adr/0014-a-model-may-find-but-not-speak.md.

SYSTEM_PROMPT = """\
You match a user's question to entries in a fixed catalogue of graph and data \
analysis methods.

Reply with JSON only, in this exact form:
{"ids": ["problem_or_method_or_family_id", ...]}

Rules:
- Each catalogue line is `- <id> (<kind>): <description>`. The id is the FIRST
  token on the line. Never return the kind, and never invent an id.
- Return every entry that could plausibly be what the user means, best match
  first, up to 6. Being generous here is safe: Gigi filters afterwards, and a
  missing entry cannot be recovered later.
- Include the `problem` ids as well as the methods. A problem is the question
  the user is really asking, and Gigi resolves it to the right method itself.
- If the question is about something else entirely -- cooking, machine learning
  training, the weather -- return {"ids": []}. That is a correct answer.
- Do not explain. Do not add prose. JSON only.

CATALOGUE
%s"""

# What a model returns and we refuse to believe. Not a real ranking -- the model
# gave an order, not a score -- but high enough to clear the relevance floor,
# because the model has already made the judgement the floor exists to make.
MODEL_SCORE = 3.0


def catalogue() -> str:
    """The closed set of things a model is allowed to choose from.

    Small enough to send whole -- a few kilobytes -- so there is no retrieval
    step in front of the retrieval step. If the registry ever outgrows that,
    this is where a first-pass filter goes.
    """
    lines = []
    for kind, entry_id, title, phrases, terms in _searchable():
        detail = next((t for t in reversed(terms) if t and t != title), "")
        synonyms = ", ".join(dict.fromkeys(p for p in phrases if p and p != title))
        # The id is the first token on the line. An earlier format put the
        # kind first, as `- [problem] community_grouping: ...`, and models
        # duly returned "problem" as an id -- correct ids alongside it, but a
        # junk entry every time. Format is prompt.
        line = f"- {entry_id} ({kind}): {title}"
        if detail:
            line += f" -- {' '.join(detail.split())[:160]}"
        if synonyms:
            line += f" (also called: {synonyms[:160]})"
        lines.append(line)
    return "\n".join(lines)


def parse_ids(reply: str) -> list[str]:
    """Pull the id list out of a model's reply, forgivingly.

    Models wrap JSON in prose or code fences however they feel that day, and a
    match lost to a stray backtick is a bad reason to fall back. Anything
    unparseable yields nothing, which the caller treats as no match.
    """
    text = (reply or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return []
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    ids = payload.get("ids") if isinstance(payload, dict) else None
    if not isinstance(ids, list):
        return []
    return [str(i) for i in ids if isinstance(i, (str, int))]


def resolve(ids: Sequence[str]) -> list[Match]:
    """Turn the model's ids into real entries, discarding anything invented.

    This is the whole safety property. The model chose from a catalogue, but it
    is not trusted to have done so: every id is looked up here, and one that
    does not resolve is dropped without comment. A model cannot add a method to
    Gigi by mentioning it.
    """
    known = {
        entry_id: (kind, title) for kind, entry_id, title, _, _ in _searchable()
    }
    matches = []
    for position, entry_id in enumerate(dict.fromkeys(ids)):
        found = known.get(entry_id)
        if found is None:
            continue
        kind, title = found
        # Decreasing with position, so the model's ordering survives into the
        # same ranking the keyword path produces.
        matches.append(Match(kind, entry_id, title, MODEL_SCORE - position * 0.1))
    return matches


def search_with_model(question: str, provider, limit: int = 6) -> list[Match]:
    """Ask a model which entries this question is about.

    Returns an empty list on any failure -- unreachable endpoint, bad key,
    unparseable reply, every id invented. The caller falls back to keywords,
    because `gigi ask` working offline is not negotiable.
    """
    try:
        reply = provider.complete(SYSTEM_PROMPT % catalogue(), question)
    except Exception:
        return []
    return resolve(parse_ids(reply))[:limit]
