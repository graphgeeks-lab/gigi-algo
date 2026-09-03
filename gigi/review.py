"""What a human should look at before merging an algorithm.

CI answers "does it pass". Review answers "is it right", and those are
different questions. This module draws the line between them explicitly:

- `checks` are things a machine settled. Read them to know what you do *not*
  have to verify by hand.
- `gaps` are absences that are not failures. Usually the next contribution.
- `by_eye` is the list a machine cannot settle. It is deliberately short,
  because a checklist nobody finishes protects nothing.

The most important item on that last list is whether `reference.py` actually
computes what `maths.definition` says. Nothing can check that, and everything
downstream depends on it -- the reference implementation is the oracle every
engine is compared against.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gigi import invariants, people, registry
from gigi.graph import list_datasets
from gigi.harness import runnable_engines, verify
from gigi.models import INVERSE_RELATIONS


@dataclass
class Check:
    """Something a machine settled."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class ByEye:
    """Something only a person can settle."""

    question: str
    where: str
    why: str


@dataclass
class Review:
    """One algorithm's review: what is settled, what is absent, what is left."""

    algorithm_id: str
    checks: list[Check] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    by_eye: list[ByEye] = field(default_factory=list)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    @property
    def ok(self) -> bool:
        return not self.failed


def review(algorithm_id: str) -> Review:
    """Assemble the review for one algorithm."""
    spec = registry.load_algorithm(algorithm_id)
    result = Review(algorithm_id=algorithm_id)
    directory = registry.algorithm_dir(algorithm_id)

    def check(name: str, passed: bool, detail: str = "") -> None:
        result.checks.append(Check(name, passed, detail))

    # --- settled by machine -------------------------------------------------
    check("spec validates against the schema", True, "loaded without error")

    check(
        "family resolves",
        registry.family_exists(spec.family),
        f"{spec.family} -> {registry.load_family(spec.family).question}"
        if registry.family_exists(spec.family)
        else f"{spec.family!r} is not in families/families.yaml",
    )

    unknown = [p for p in spec.credits.everyone() if not people.exists(p)]
    check("every credited person resolves", not unknown, ", ".join(unknown))

    missing_checks = [i.id for i in spec.maths.checkable() if not invariants.known(i.id)]
    check(
        "every checkable invariant is implemented",
        not missing_checks,
        ", ".join(missing_checks) or f"{len(spec.maths.checkable())} invariant(s)",
    )

    for name in ("maths.md", "notes.md", "implementations/reference.py"):
        check(f"{name} exists", (directory / name).is_file())

    declared = {e for e, s in spec.engines.items() if s.supported}
    implemented = set(registry.implemented_engines(algorithm_id))
    check(
        "declared engines all have implementations",
        declared <= implemented,
        ", ".join(sorted(declared - implemented)),
    )

    unmirrored = []
    known = set(registry.list_algorithms())
    for relationship in spec.relationships:
        if relationship.algorithm not in known:
            continue
        other = registry.load_algorithm(relationship.algorithm)
        expected = INVERSE_RELATIONS[relationship.kind]
        if not any(
            r.algorithm == algorithm_id and r.kind == expected for r in other.relationships
        ):
            unmirrored.append(f"{relationship.algorithm} does not say {expected.value}")
    check("relationships are mirrored", not unmirrored, "; ".join(unmirrored))

    report = verify(spec)
    check(
        "engines agree where the registry says they agree",
        not report.undeclared_differences,
        f"{len(report.runs)} runs, {len(report.undeclared_differences)} undeclared difference(s)",
    )
    broken = [r for r in report.runs if r.failed_invariants]
    check(
        "invariants hold on every run",
        not broken,
        f"{sum(len(r.invariants) for r in report.runs)} assertions"
        if not broken
        else f"{broken[0].engine} violated {broken[0].failed_invariants[0].invariant_id}",
    )
    unreproduced = [
        c for c in report.divergence_checks if not c.reproduced and c.observed != "skipped"
    ]
    check(
        "declared divergences still reproduce",
        not unreproduced,
        ", ".join(c.divergence_id for c in unreproduced)
        or f"{len(report.divergence_checks)} declared",
    )

    # --- absences worth noticing, but not failures --------------------------
    for engine in sorted(set(registry.ENGINE_NAMES) - implemented):
        result.gaps.append(f"no {engine} implementation yet")

    uncovered = sorted(set(list_datasets()) - set(spec.datasets))
    if uncovered:
        result.gaps.append(f"not run against: {', '.join(uncovered)}")

    for choice in spec.maths.under_determined:
        if not choice.divergence and not choice.datasets:
            result.gaps.append(
                f"choice point {choice.id!r} has no fixture -- nothing tests which "
                f"answer the engines chose"
            )

    for divergence in spec.divergences:
        if not divergence.discovered_by:
            result.gaps.append(f"divergence {divergence.id!r} credits nobody")

    if not spec.provenance.original_work:
        result.gaps.append("no original work cited in provenance")

    skipped = [c for c in report.divergence_checks if c.observed == "skipped"]
    for check_result in skipped:
        result.gaps.append(
            f"divergence {check_result.divergence_id!r} not checked here: {check_result.note}"
        )

    # --- what a person has to decide ---------------------------------------
    result.by_eye = _by_eye(spec, algorithm_id)
    return result


def _by_eye(spec, algorithm_id: str) -> list[ByEye]:
    """Short on purpose. A checklist nobody finishes protects nothing."""
    items = [
        ByEye(
            question="Does the reference implementation compute what the definition says?",
            where=f"algorithms/{algorithm_id}/implementations/reference.py "
            f"beside `maths.definition`",
            why="It is the oracle every engine is checked against. Nothing else "
            "checks this, and everything downstream assumes it.",
        ),
        ByEye(
            question="Could someone learn the algorithm from the reference implementation?",
            where=f"algorithms/{algorithm_id}/implementations/reference.py",
            why="It is a teaching artifact as much as an oracle. If it needs a "
            "comment to explain a trick, the trick probably does not belong.",
        ),
        ByEye(
            question="Do maths.md and the `maths:` block say the same thing?",
            where=f"algorithms/{algorithm_id}/maths.md",
            why="The one seam in the design that nothing verifies. They are "
            "reviewed together or they drift.",
        ),
    ]

    if spec.divergences:
        items.append(
            ByEye(
                question="Is each divergence the engine's behaviour, and not our bug?",
                where=f"algorithms/{algorithm_id}/notes.md",
                why="A divergence entry accuses a library of doing something "
                "surprising. It should say why that is the library's choice.",
            )
        )

    if spec.provenance.original_authors or spec.provenance.precursors:
        items.append(
            ByEye(
                question="Is the attribution honest -- precursors real, nothing overclaimed?",
                where="`provenance` in algorithm.yaml",
                why="Contested credit belongs in attribution_notes rather than "
                "being resolved silently in our favour.",
            )
        )

    if registry.family_exists(spec.family):
        family = registry.load_family(spec.family)
        items.append(
            ByEye(
                question=f'Does this algorithm answer "{family.question}"?',
                where="`family` in algorithm.yaml",
                why="A family is a question, not a label. If the answer is no, "
                "the family is wrong even when the label sounds right.",
            )
        )

    return items
