"""The people registry, and the reverse index from a person to their work.

Two rules shape this module:

- Attribution is a claim like any other, so an id that does not resolve fails
  the test suite rather than rendering as a dead link.
- Contributions are described as lineage, never as a score. "Wrote the
  reference implementation for PageRank and found the NetworkX weight
  divergence" says something; "423 points" does not, and rewards volume.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from gigi.models import Person
from gigi.paths import repo_root


class PeopleError(Exception):
    pass


def people_file() -> Path:
    override = os.environ.get("GIGI_PEOPLE_FILE")
    return Path(override).resolve() if override else repo_root() / "people" / "people.yaml"


@lru_cache(maxsize=1)
def _load() -> dict[str, Person]:
    path = people_file()
    if not path.is_file():
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise PeopleError(f"{path}: expected a list of people")

    records: dict[str, Person] = {}
    for entry in raw:
        try:
            person = Person.model_validate(entry)
        except ValidationError as exc:
            raise PeopleError(f"{path}: {exc}") from exc
        if person.id in records:
            raise PeopleError(f"{path}: duplicate person id {person.id!r}")
        records[person.id] = person
    return records


def list_people() -> list[Person]:
    return sorted(_load().values(), key=lambda person: person.name)


def get_person(person_id: str) -> Person:
    people = _load()
    if person_id not in people:
        raise PeopleError(f"unknown person {person_id!r} -- add them to people/people.yaml")
    return people[person_id]


def exists(person_id: str) -> bool:
    return person_id in _load()


@dataclass
class Contribution:
    """One thing a person did, and to what."""

    algorithm_id: str
    role: str
    detail: str = ""


@dataclass
class Profile:
    """Everything the registry records about one person's work."""

    person: Person
    contributions: list[Contribution] = field(default_factory=list)
    discoveries: list[Contribution] = field(default_factory=list)

    @property
    def algorithms(self) -> list[str]:
        return sorted({c.algorithm_id for c in [*self.contributions, *self.discoveries]})


# How each Credits field reads on a profile page.
_CREDIT_ROLES = [
    ("stewards", "steward"),
    ("spec_curators", "specification"),
    ("reference_implementation", "reference implementation"),
    ("verifier_authors", "verifier"),
    ("dataset_curators", "dataset curation"),
    ("reviewers", "review"),
]


def profile(person_id: str) -> Profile:
    """Everything the registry says this person did, gathered by reading the
    specs rather than by maintaining a second list that can drift."""
    from gigi import registry

    result = Profile(person=get_person(person_id))

    for algorithm_id in registry.list_algorithms():
        spec = registry.load_algorithm(algorithm_id)

        for attribute, label in _CREDIT_ROLES:
            if person_id in getattr(spec.credits, attribute):
                result.contributions.append(Contribution(algorithm_id, label))

        for engine, contributors in spec.credits.adapter_contributors.items():
            if person_id in contributors:
                result.contributions.append(
                    Contribution(algorithm_id, "engine adapter", engine)
                )

        for divergence in spec.divergences:
            if person_id in divergence.discovered_by:
                result.discoveries.append(
                    Contribution(algorithm_id, "divergence", divergence.id)
                )

    return result


def referenced_ids() -> dict[str, list[str]]:
    """Every person id the registry mentions, mapped to where it was mentioned.

    Used by the test suite to prove that attribution resolves.
    """
    from gigi import registry

    found: dict[str, list[str]] = {}
    for algorithm_id in registry.list_algorithms():
        spec = registry.load_algorithm(algorithm_id)
        for person_id in spec.credits.everyone():
            found.setdefault(person_id, []).append(f"{algorithm_id}: gigi credits")
        for divergence in spec.divergences:
            for person_id in divergence.discovered_by:
                found.setdefault(person_id, []).append(
                    f"{algorithm_id}: divergence {divergence.id}"
                )
    return found
