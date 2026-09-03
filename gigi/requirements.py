"""What an algorithm entry must have before it is believed, tier by tier.

The maturity ladder is only real if each rung has a stated price. This module
is that price list, in one place, so that `gigi review`, the test suite and
CONTRIBUTING.md cannot drift into three different opinions about what a
`stable` algorithm needs.

Each requirement names the lowest tier at which it is mandatory. Below that
tier it is still checked and still reported -- as something recommended, so a
contributor can see what promotion would take.

    frontier / historical   the entry exists and resolves
    emerging                the maths is stated and independently checked
    stable                  every claim is testable, and has been tested
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from gigi import people, registry
from gigi.models import AlgorithmSpec, Maturity

# How far up the ladder a tier is. Historical is frozen, so it owes no more
# than frontier does; it simply is not recommended.
RANK: dict[Maturity, int] = {
    Maturity.frontier: 0,
    Maturity.historical: 0,
    Maturity.emerging: 1,
    Maturity.stable: 2,
}

KNOWN_ANSWERS_EMERGING = 2
KNOWN_ANSWERS_STABLE = 4
DEGENERATE_FIXTURES = ("empty", "single-node")


@dataclass(frozen=True)
class Requirement:
    """One rung-gated condition, and the check that decides it."""

    id: str
    description: str
    mandatory_from: Maturity
    check: Callable[[AlgorithmSpec], "str | None"]  # None when met, else why not


@dataclass
class Outcome:
    """A requirement applied to one spec: met or not, binding or advisory."""

    requirement: Requirement
    met: bool
    required: bool
    detail: str = ""


# --- the checks ---------------------------------------------------------------


def _reference_exists(spec: AlgorithmSpec) -> str | None:
    if registry.has_implementation(spec.id, "reference"):
        return None
    return "no implementations/reference.py"


def _family_resolves(spec: AlgorithmSpec) -> str | None:
    if registry.family_exists(spec.family):
        return None
    return f"family {spec.family!r} is not in families/families.yaml"


def _people_resolve(spec: AlgorithmSpec) -> str | None:
    ids = set(spec.credits.everyone())
    for divergence in spec.divergences:
        ids.update(divergence.discovered_by)
    unknown = sorted(i for i in ids if not people.exists(i))
    return f"unknown person id(s): {', '.join(unknown)}" if unknown else None


def _maths_stated(spec: AlgorithmSpec) -> str | None:
    if spec.maths.definition and spec.maths.definition.statement.strip():
        return None
    return "maths.definition is missing"


def _has_checkable_invariant(spec: AlgorithmSpec) -> str | None:
    if spec.maths.checkable():
        return None
    return "no invariant with check: true -- nothing about the output is asserted"


def _notes_written(spec: AlgorithmSpec) -> str | None:
    path = registry.algorithm_dir(spec.id) / "notes.md"
    if path.is_file() and len(path.read_text(encoding="utf-8").strip()) > 200:
        return None
    return "notes.md is missing or too short to say what was measured"


def _known_answers(minimum: int) -> Callable[[AlgorithmSpec], "str | None"]:
    def _check(spec: AlgorithmSpec) -> str | None:
        from gigi.knownanswers import load_cases

        count = len(load_cases(spec.id))
        if count >= minimum:
            return None
        return f"{count} known-answer case(s) in tests/expected.yaml, need {minimum}"

    return _check


def _known_answers_derived(spec: AlgorithmSpec) -> str | None:
    from gigi.knownanswers import load_cases

    weak = [c.id for c in load_cases(spec.id) if len(c.derived.strip()) < 12]
    if weak:
        return f"case(s) with no real derivation: {', '.join(weak)}"
    return None


def _provenance_cited(spec: AlgorithmSpec) -> str | None:
    if spec.provenance.original_authors and spec.provenance.original_work:
        return None
    return "provenance needs original_authors and original_work"


def _divergences_testable(spec: AlgorithmSpec) -> str | None:
    prose_only = [d.id for d in spec.divergences if d.detect is None]
    if prose_only:
        return f"divergence(s) with no detect block: {', '.join(prose_only)}"
    return None


def _divergences_have_choice_points(spec: AlgorithmSpec) -> str | None:
    covered = {d for c in spec.maths.under_determined for d in c.divergences}
    orphans = [d.id for d in spec.divergences if d.id not in covered]
    if orphans:
        return f"divergence(s) not tied to a choice in the definition: {', '.join(orphans)}"
    return None


def _divergences_credited(spec: AlgorithmSpec) -> str | None:
    anonymous = [d.id for d in spec.divergences if not d.discovered_by]
    if anonymous:
        return f"divergence(s) crediting nobody: {', '.join(anonymous)}"
    return None


def _degenerate_fixtures(spec: AlgorithmSpec) -> str | None:
    missing = [d for d in DEGENERATE_FIXTURES if d not in spec.datasets]
    if missing:
        return f"not run against {', '.join(missing)}"
    return None


def _several_engines(spec: AlgorithmSpec) -> str | None:
    engines = [e for e in registry.implemented_engines(spec.id) if e != "reference"]
    if len(engines) >= 2:
        return None
    return f"{len(engines)} non-reference engine(s); cross-engine evidence needs two"


REQUIREMENTS: list[Requirement] = [
    Requirement("reference_exists", "a readable reference implementation exists", Maturity.frontier, _reference_exists),
    Requirement("family_resolves", "the family is in families/families.yaml", Maturity.frontier, _family_resolves),
    Requirement("people_resolve", "every credited person is in people/people.yaml", Maturity.frontier, _people_resolve),
    Requirement("maths_stated", "the definition is stated in maths.definition", Maturity.emerging, _maths_stated),
    Requirement("invariant_checked", "at least one invariant is asserted on every run", Maturity.emerging, _has_checkable_invariant),
    Requirement("known_answers", f"at least {KNOWN_ANSWERS_EMERGING} known-answer cases", Maturity.emerging, _known_answers(KNOWN_ANSWERS_EMERGING)),
    Requirement("known_answers_derived", "every known answer says how it was derived", Maturity.emerging, _known_answers_derived),
    Requirement("divergences_credited", "every divergence names who found it", Maturity.emerging, _divergences_credited),
    Requirement("notes_written", "notes.md records what was measured", Maturity.emerging, _notes_written),
    Requirement("provenance_cited", "original authors and work are cited", Maturity.stable, _provenance_cited),
    Requirement("divergences_testable", "every divergence has a detect block", Maturity.stable, _divergences_testable),
    Requirement("divergences_explained", "every divergence is tied to a choice in the definition", Maturity.stable, _divergences_have_choice_points),
    Requirement("known_answers_thorough", f"at least {KNOWN_ANSWERS_STABLE} known-answer cases", Maturity.stable, _known_answers(KNOWN_ANSWERS_STABLE)),
    Requirement("degenerate_fixtures", "runs against the empty and single-node fixtures", Maturity.stable, _degenerate_fixtures),
    Requirement("several_engines", "two or more engines besides the reference", Maturity.stable, _several_engines),
]


def check(spec: AlgorithmSpec) -> list[Outcome]:
    """Every requirement, met or not, required at this tier or merely
    recommended. In ladder order, so the list reads as a path to promotion."""
    outcomes = []
    for requirement in REQUIREMENTS:
        detail = requirement.check(spec)
        outcomes.append(
            Outcome(
                requirement=requirement,
                met=detail is None,
                required=RANK[requirement.mandatory_from] <= RANK[spec.maturity],
                detail=detail or "",
            )
        )
    return outcomes


def unmet(spec: AlgorithmSpec) -> list[Outcome]:
    """Required at this tier and not met. Non-empty means the entry is claiming
    a maturity it has not earned."""
    return [o for o in check(spec) if o.required and not o.met]


def next_tier(spec: AlgorithmSpec) -> tuple[Maturity | None, list[Outcome]]:
    """What promotion would take: the tier above, and what it still lacks."""
    ladder = [Maturity.frontier, Maturity.emerging, Maturity.stable]
    if spec.maturity not in ladder or spec.maturity == Maturity.stable:
        return None, []
    target = ladder[ladder.index(spec.maturity) + 1]
    lacking = [
        o for o in check(spec)
        if not o.met and RANK[o.requirement.mandatory_from] <= RANK[target]
    ]
    return target, lacking
