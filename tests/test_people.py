"""Attribution is a claim, and claims get checked.

A dead person id renders as a broken link on a public profile page and, worse,
quietly drops someone's credit. So the same rule applies here as to
divergences: if the registry says it, the test suite proves it.
"""

from __future__ import annotations

import pytest
import yaml

from gigi import people, registry
from gigi.paths import repo_root

ALGORITHMS = registry.list_algorithms()


def test_people_registry_loads():
    assert people.list_people(), "people/people.yaml is empty or missing"


def test_every_referenced_person_exists():
    unknown = {
        person_id: where
        for person_id, where in people.referenced_ids().items()
        if not people.exists(person_id)
    }
    assert not unknown, f"unknown person ids referenced: {unknown}"


def test_every_person_is_referenced():
    """The other direction. A profile with nothing on it is worse than no
    profile, so people.yaml should not accumulate placeholder entries."""
    referenced = people.referenced_ids()
    orphans = [p.id for p in people.list_people() if p.id not in referenced]
    assert not orphans, f"people with no contributions recorded: {orphans}"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_stable_algorithms_have_provenance(algorithm_id):
    """A stable entry that cannot say where the algorithm came from is not
    finished."""
    spec = registry.load_algorithm(algorithm_id)
    if spec.maturity.value != "stable":
        return
    assert spec.provenance.original_authors, f"{algorithm_id}: no original authors"
    assert spec.provenance.original_work, f"{algorithm_id}: no original work cited"


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_provenance_is_separate_from_credits(algorithm_id):
    """The two attribution layers must not be conflated: an original author is
    a historical fact, a Gigi contributor is a person in people.yaml."""
    spec = registry.load_algorithm(algorithm_id)
    historical = {author.name.lower() for author in spec.provenance.original_authors}
    contributors = {people.get_person(i).name.lower() for i in spec.credits.everyone()}
    assert not (historical & contributors), (
        f"{algorithm_id}: the same name appears as both an original author and "
        f"a Gigi contributor -- if that is genuinely true, say so in "
        f"attribution_notes rather than letting the layers blur"
    )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_precursor_algorithm_ids_are_plausible(algorithm_id):
    """A precursor may point at an algorithm we have not added yet, but if we
    have added it, the id must be right."""
    spec = registry.load_algorithm(algorithm_id)
    known = set(ALGORITHMS)
    for precursor in spec.provenance.precursors:
        if precursor.algorithm_id and precursor.algorithm_id in known:
            registry.load_algorithm(precursor.algorithm_id)


def test_profile_reports_lineage_not_a_score():
    profile = people.profile("dennis-irorere")
    assert profile.algorithms, "profile should list the algorithms worked on"
    assert any(c.role == "reference implementation" for c in profile.contributions)
    assert profile.discoveries, "divergence discoveries should appear separately"


def test_citation_authors_are_registered_people():
    """CITATION.cff and people.yaml must not drift apart."""
    path = repo_root() / "CITATION.cff"
    if not path.is_file():
        pytest.skip("no CITATION.cff yet")

    citation = yaml.safe_load(path.read_text(encoding="utf-8"))
    known = {p.name for p in people.list_people()}
    for author in citation.get("authors", []):
        full = f"{author.get('given-names', '')} {author.get('family-names', '')}".strip()
        assert full in known, f"{full} is in CITATION.cff but not people/people.yaml"
