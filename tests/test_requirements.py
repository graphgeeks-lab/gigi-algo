"""Every algorithm meets the requirements of the maturity it claims.

`gigi/requirements.py` is the single price list for the maturity ladder. This
file makes it binding: an entry that says `stable` and lacks something stable
requires is claiming a maturity it has not earned, and the build says so.
"""

from __future__ import annotations

import pytest

from gigi import registry, requirements
from gigi.models import Maturity

ALGORITHMS = registry.list_methods()


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_algorithm_meets_the_requirements_of_its_maturity(method_id):
    spec = registry.load_method(method_id)
    lacking = requirements.unmet(spec)
    assert not lacking, (
        f"{method_id} claims `{spec.maturity.value}` but lacks:\n  "
        + "\n  ".join(f"{o.requirement.id}: {o.detail}" for o in lacking)
    )


@pytest.mark.parametrize("method_id", ALGORITHMS)
def test_every_requirement_is_reported_not_just_the_failures(method_id):
    """`gigi review` shows the whole ladder, so every requirement must produce
    an outcome -- met or not, required or recommended."""
    outcomes = requirements.check(registry.load_method(method_id))
    assert {o.requirement.id for o in outcomes} == {r.id for r in requirements.REQUIREMENTS}


def test_ladder_is_monotone():
    """Nothing required at a lower tier may be optional at a higher one."""
    ranks = requirements.RANK
    assert ranks[Maturity.frontier] < ranks[Maturity.emerging] < ranks[Maturity.stable]
    assert ranks[Maturity.historical] == ranks[Maturity.frontier]


def test_stable_requires_strictly_more_than_emerging():
    stable_only = [
        r.id for r in requirements.REQUIREMENTS if r.mandatory_from == Maturity.stable
    ]
    assert stable_only, "stable must cost something emerging does not"
    assert "divergences_testable" in stable_only
    assert "known_answers_thorough" in stable_only


def test_next_tier_names_what_promotion_takes():
    """For an emerging algorithm, the path to stable is a concrete list."""
    emerging = [a for a in ALGORITHMS if registry.load_method(a).maturity == Maturity.emerging]
    if not emerging:
        pytest.skip("no emerging algorithm to test promotion against")
    target, lacking = requirements.next_tier(registry.load_method(emerging[0]))
    assert target == Maturity.stable
    for outcome in lacking:
        assert not outcome.met
        assert outcome.detail, "an unmet requirement must say what is missing"


def test_stable_has_no_next_tier():
    stable = [a for a in ALGORITHMS if registry.load_method(a).maturity == Maturity.stable]
    if not stable:
        pytest.skip("no stable algorithm")
    target, lacking = requirements.next_tier(registry.load_method(stable[0]))
    assert target is None and lacking == []


def test_requirements_have_distinct_ids_and_descriptions():
    ids = [r.id for r in requirements.REQUIREMENTS]
    assert len(ids) == len(set(ids))
    for requirement in requirements.REQUIREMENTS:
        assert requirement.description and not requirement.description.endswith(".")
