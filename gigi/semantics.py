"""Does this method read the user's data the way the user means it?

The registry knows what a method expects: PageRank reads an edge weight as
*strength*, so a larger value is a stronger relationship. Dijkstra reads the
same column as *cost*, where a larger value is worse. Nothing in the data says
which is intended, and running both on a column called `distance` asks two
contradictory questions while being told nothing.

This module supplies the missing half — a guess at what the user's column
actually holds — and compares it against what the method assumes. Two rules
shape the whole thing:

- **It asks; it never rewrites.** No value is transformed, no parameter is
  changed, nothing is refused. The output is a question for a person.
- **The vocabulary is data.** `semantics/column_meanings.yaml`, not a dict in
  here, so adding a hint is a one-line change and a column that matches
  nothing produces no finding rather than a bad one.

An Apache OSSIE semantic model, where one exists, is better evidence than any
name-based guess and should take precedence over this. See docs/ONTOLOGY.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from gigi.graph import GraphData
from gigi.models import MethodSpec, SemanticInterpretation
from gigi.paths import column_meanings_file

# A finding this severe is worth interrupting for; anything else is a note.
SERIOUS = {"dangerous"}


@dataclass
class ColumnMeaning:
    """One row of the hint vocabulary."""

    meaning: str
    hints: list[str]


@dataclass
class Finding:
    """A mismatch, or a match worth mentioning, between data and method."""

    column: str
    inferred_meaning: str | None
    subject: str
    semantic_role: str
    higher_means: str | None
    fit: str
    note: str

    @property
    def serious(self) -> bool:
        return self.fit in SERIOUS

    def question(self) -> str:
        """The sentence to put in front of a person."""
        if self.inferred_meaning is None:
            return (
                f"Column `{self.column}` does not look like anything we recognise. "
                f"This method reads it as {self.semantic_role}"
                + (f", where higher means {self.higher_means}" if self.higher_means else "")
                + ". Is that what it holds?"
            )
        looks_like = self.inferred_meaning.replace("_", " ")
        reads_it_as = f"reads it as {self.semantic_role}" + (
            f", where higher means {self.higher_means}" if self.higher_means else ""
        )
        if self.serious:
            return (
                f"Column `{self.column}` looks like {looks_like}, and this method "
                f"{reads_it_as}. Did you intend to invert or transform it?"
            )
        if self.fit == "unknown":
            # The column is readable, but this method has not said what it makes
            # of that meaning. Silence is not reassurance.
            return (
                f"Column `{self.column}` looks like {looks_like}. This method does "
                f"not say how it reads that; it {reads_it_as}. Worth checking."
            )
        return f"Column `{self.column}` looks like {looks_like}, read here as {self.semantic_role}."


@lru_cache(maxsize=1)
def vocabulary() -> list[ColumnMeaning]:
    """The hint table, or an empty one if the file is absent."""
    path = column_meanings_file()
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [ColumnMeaning(meaning=r["meaning"], hints=list(r.get("hints", []))) for r in raw]


def infer_meaning(column: str) -> str | None:
    """What a column name suggests, or None when it suggests nothing.

    Matches on whole tokens rather than substrings, so `distance` matches and
    `distance_rank` matches, while `predistance` does not accidentally.
    """
    tokens = {t for t in re.split(r"[^a-z0-9]+", column.lower()) if t}
    if not tokens:
        return None
    for entry in vocabulary():
        if tokens & set(entry.hints):
            return entry.meaning
    return None


def _meaning_fit(
    interpretation: SemanticInterpretation, meaning: str | None
) -> tuple[str, str]:
    """How well an inferred meaning sits with what the method assumes."""
    for declared in interpretation.common_domain_meanings:
        if declared.meaning == meaning:
            return declared.fit, (declared.note or "")
    return "unknown", ""


def check_graph(spec: MethodSpec, graph: GraphData) -> list[Finding]:
    """Compare this graph's columns against what the method says it reads.

    Only edge weight today, because that is the only part of a graph whose
    meaning is genuinely open. When vectors and record pairs arrive, their
    subjects join the same loop.
    """
    column = graph.weight_column
    if column is None:
        return []

    findings: list[Finding] = []
    meaning = infer_meaning(column)
    for interpretation in spec.semantic_interpretations:
        if interpretation.subject != "edge_weight":
            continue
        fit, note = _meaning_fit(interpretation, meaning)
        if fit == "strong":
            continue  # what the method assumes; nothing to say
        findings.append(
            Finding(
                column=column,
                inferred_meaning=meaning,
                subject=interpretation.subject,
                semantic_role=interpretation.semantic_role,
                higher_means=interpretation.higher_means,
                fit=fit,
                note=note,
            )
        )
    return findings


def divergences_for_dataset(spec: MethodSpec, dataset_id: str | None) -> list[str]:
    """Declared divergences this exact fixture is named in.

    Derived, not guessed: a divergence names the fixtures it reproduces on, so
    this says "the thing we measured happens to your data" rather than "it
    might".
    """
    if dataset_id is None:
        return []
    return [
        d.id
        for d in spec.divergences
        if d.detect and dataset_id in d.detect.datasets
    ]
