"""What a human should look at before merging an algorithm.

CI answers "does it pass". Review answers "is it right", and those are
different questions. This module draws the line between them explicitly:

- `checks` are things a machine settled -- the requirements of the claimed
  maturity, plus what happened when everything was actually run. Read them to
  know what you do *not* have to verify by hand.
- `gaps` are absences that are not failures at this tier: requirements the
  next rung of the ladder would impose, fixtures not yet covered. Usually the
  next contribution.
- `by_eye` is the list a machine cannot settle. It is deliberately short,
  because a checklist nobody finishes protects nothing.

The most important item on that last list is whether `reference.py` computes
what `maths.definition` says. Known-answer cases check it partially -- against
values derived by hand -- and that is as close as automation gets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gigi import knownanswers, registry, requirements
from gigi.graph import list_datasets
from gigi.harness import verify


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
    maturity: str
    checks: list[Check] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    by_eye: list[ByEye] = field(default_factory=list)
    promotion: tuple[str | None, list[str]] = (None, [])

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    @property
    def ok(self) -> bool:
        return not self.failed


def review(algorithm_id: str) -> Review:
    """Assemble the review for one algorithm."""
    spec = registry.load_algorithm(algorithm_id)
    result = Review(algorithm_id=algorithm_id, maturity=spec.maturity.value)

    # --- the requirements of the tier it claims -----------------------------
    for outcome in requirements.check(spec):
        if outcome.required:
            result.checks.append(
                Check(outcome.requirement.description, outcome.met, outcome.detail)
            )
        elif not outcome.met:
            result.gaps.append(
                f"{outcome.requirement.description} "
                f"(needed for {outcome.requirement.mandatory_from.value}): {outcome.detail}"
            )

    # --- what happened when it was run ---------------------------------------
    cases = knownanswers.load_cases(algorithm_id)
    failed_cases = [
        r for r in (knownanswers.run_case(algorithm_id, c) for c in cases) if not r.passed
    ]
    result.checks.append(
        Check(
            "reference gives every known answer",
            not failed_cases,
            f"{len(cases)} case(s), derived by hand"
            if not failed_cases
            else "; ".join(f"{r.case_id}: {r.detail}" for r in failed_cases),
        )
    )

    report = verify(spec, allow_frontier=True)
    result.checks.append(
        Check(
            "engines agree where the registry says they agree",
            not report.undeclared_differences,
            f"{len(report.runs)} runs, {len(report.explained_differences)} explained, "
            f"{len(report.undeclared_differences)} undeclared",
        )
    )
    unexplained_invariants = [
        d for d in report.undeclared_differences if d.detail.startswith("violated")
    ]
    result.checks.append(
        Check(
            "invariants hold on every run, or the failure is a declared divergence",
            not unexplained_invariants,
            f"{sum(len(r.invariants) for r in report.runs)} assertions"
            if not unexplained_invariants
            else unexplained_invariants[0].detail,
        )
    )
    unreproduced = [
        c for c in report.divergence_checks if not c.reproduced and c.observed != "skipped"
    ]
    result.checks.append(
        Check(
            "declared divergences still reproduce",
            not unreproduced,
            ", ".join(c.divergence_id for c in unreproduced)
            or f"{len(report.divergence_checks)} declared",
        )
    )

    # --- absences worth noticing ---------------------------------------------
    implemented = set(registry.implemented_engines(algorithm_id))
    for engine in sorted(set(registry.ENGINE_NAMES) - implemented):
        result.gaps.append(f"no {engine} implementation yet")
    uncovered = sorted(set(list_datasets()) - set(spec.datasets))
    if uncovered:
        result.gaps.append(f"not run against: {', '.join(uncovered)}")
    for choice in spec.maths.under_determined:
        if not choice.divergences and not choice.datasets:
            result.gaps.append(
                f"choice point {choice.id!r} has no fixture -- nothing tests which "
                f"answer the engines chose"
            )
    for check in report.divergence_checks:
        if check.observed == "skipped":
            result.gaps.append(f"divergence {check.divergence_id!r} not checked here: {check.note}")

    target, lacking = requirements.next_tier(spec)
    result.promotion = (
        target.value if target else None,
        [f"{o.requirement.description}: {o.detail}" for o in lacking],
    )

    result.by_eye = _by_eye(spec, algorithm_id)
    return result


def _by_eye(spec, algorithm_id: str) -> list[ByEye]:
    """Short on purpose. A checklist nobody finishes protects nothing."""
    items = [
        ByEye(
            question="Does the reference implementation compute what the definition says?",
            where=f"algorithms/{algorithm_id}/implementations/reference.py "
            f"beside `maths.definition`",
            why="It is the oracle every engine is checked against. The known-answer "
            "cases check it against hand-derived values; you check the rest.",
        ),
        ByEye(
            question="Are the known answers really derived, not observed?",
            where=f"algorithms/{algorithm_id}/tests/expected.yaml, the `derived` fields",
            why="A case whose expected value came from running the code checks "
            "the code against itself. Read each derivation and ask whether you "
            "could have reached the number without the software.",
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
                "surprising. It should say why that is the library's choice -- or "
                "say plainly that the rule could not be derived.",
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
                question=(
                    "Does this algorithm answer the family's question -- "
                    f'"{family.question.rstrip("?")}"?'
                ),
                where="`family` in algorithm.yaml",
                why="A family is a question, not a label. If the answer is no, "
                "the family is wrong even when the label sounds right.",
            )
        )

    return items
