"""Families and relationships form a graph, and it has to be a consistent one.

The registry is not a list of documents; it is a graph of algorithms, families,
people, fixtures and findings. Something reading it should be able to traverse
that graph and trust what it finds, which means the edges are checked the same
way every other claim here is.
"""

from __future__ import annotations

import pytest

from gigi import people, registry
from gigi.models import INVERSE_RELATIONS

ALGORITHMS = registry.list_algorithms()
FAMILIES = [family.id for family in registry.list_families()]


def test_families_exist():
    assert FAMILIES, "families/families.yaml is empty or missing"


@pytest.mark.parametrize("family_id", FAMILIES)
def test_family_is_a_question_not_a_label(family_id):
    family = registry.load_family(family_id)
    assert family.question.strip().endswith("?"), (
        f"{family_id}: `question` should be the question the family answers, "
        f"which is what makes it useful for choosing within it"
    )
    assert family.summary.strip(), f"{family_id}: no summary"


@pytest.mark.parametrize("family_id", FAMILIES)
def test_family_links_resolve(family_id):
    family = registry.load_family(family_id)
    if family.parent:
        assert registry.family_exists(family.parent), (
            f"{family_id}: unknown parent {family.parent!r}"
        )
    for related in family.related:
        assert registry.family_exists(related), (
            f"{family_id}: unknown related family {related!r}"
        )
        assert related != family_id, f"{family_id}: related to itself"
    for steward in family.stewards:
        assert people.exists(steward), f"{family_id}: unknown steward {steward!r}"


@pytest.mark.parametrize("family_id", FAMILIES)
def test_family_hierarchy_has_no_cycles(family_id):
    seen: set[str] = set()
    current = family_id
    while current:
        assert current not in seen, f"cycle in family hierarchy at {current!r}"
        seen.add(current)
        current = registry.load_family(current).parent


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_algorithm_family_resolves(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    assert registry.family_exists(spec.family), (
        f"{algorithm_id}: family {spec.family!r} is not in families/families.yaml "
        f"(known: {', '.join(FAMILIES)})"
    )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_relationships_are_well_formed(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    for relationship in spec.relationships:
        assert relationship.algorithm != algorithm_id, (
            f"{algorithm_id} is related to itself"
        )
        if relationship.kind.value == "equivalent_under":
            assert relationship.condition, (
                f"{algorithm_id} -> {relationship.algorithm}: equivalent_under "
                f"needs the condition under which the two coincide, or it says "
                f"nothing an agent can use"
            )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_relationships_are_mirrored(algorithm_id):
    """If A generalises B, then B must say it specialises A.

    Only enforced when the other algorithm exists: pointing at one we have not
    written yet is how the roadmap gets recorded.
    """
    spec = registry.load_algorithm(algorithm_id)
    known = set(ALGORITHMS)

    for relationship in spec.relationships:
        if relationship.algorithm not in known:
            continue
        other = registry.load_algorithm(relationship.algorithm)
        expected = INVERSE_RELATIONS[relationship.kind]
        mirrored = any(
            r.algorithm == algorithm_id and r.kind == expected
            for r in other.relationships
        )
        assert mirrored, (
            f"{algorithm_id} says it {relationship.kind.value} "
            f"{relationship.algorithm}, but {relationship.algorithm} does not "
            f"say it {expected.value} {algorithm_id}"
        )


def test_precursors_and_relationships_do_not_contradict():
    """`provenance.precursors` is history; `relationships` is structure. An
    algorithm may be both a precursor and a special case, but it should not be
    claimed as a precursor of itself."""
    for algorithm_id in ALGORITHMS:
        spec = registry.load_algorithm(algorithm_id)
        for precursor in spec.provenance.precursors:
            assert precursor.algorithm_id != algorithm_id
