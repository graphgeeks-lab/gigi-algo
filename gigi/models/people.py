"""Who did the work, and who created the thing.

Four questions that get collapsed into one `inventor:` field and should not be:
who created the method, who implemented it here, who verified it, who found the
divergence. See docs/adr/0007-attribution-has-layers.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    """What a person does in Gigi, which is a different question from what they
    did in the history of the algorithm. See `Provenance` versus `Credits`."""

    algorithm_steward = "algorithm-steward"
    spec_curator = "spec-curator"
    reference_author = "reference-author"
    verifier_author = "verifier-author"
    evaluator_author = "evaluator-author"
    adapter_author = "adapter-author"
    dataset_curator = "dataset-curator"
    divergence_discoverer = "divergence-discoverer"
    benchmark_maintainer = "benchmark-maintainer"
    frontier_researcher = "frontier-researcher"
    reviewer = "reviewer"


class Person(BaseModel):
    """A record in `people/people.yaml`. Identity, not score."""

    id: str
    name: str

    # Handles, not URLs -- the site knows how to build the link, and a handle
    # survives a platform changing its URL scheme.
    github: str | None = None
    linkedin: str | None = None
    orcid: str | None = None
    website: str | None = None
    # Anything else: mastodon, bluesky, scholar, a blog. Free-form on purpose;
    # we should not need a schema change every time a platform appears.
    links: dict[str, str] = Field(default_factory=dict)

    affiliation: str | None = None
    interests: list[str] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)


class OriginalAuthor(BaseModel):
    name: str
    orcid: str | None = None
    note: str | None = None


class OriginalWork(BaseModel):
    """The publication an algorithm should be cited from."""

    title: str
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None


class Precursor(BaseModel):
    """Earlier work the algorithm builds on, or an independent discovery.

    Kept structured rather than as prose because "PageRank descends from Katz
    centrality" is a claim a reader may want to follow.
    """

    name: str
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    method_id: str | None = None
    note: str | None = None


class Provenance(BaseModel):
    """Where the algorithm came from, historically.

    Deliberately not a single `inventor` field. Algorithms have precursors,
    independent discoveries, later generalisations, and famous names that are
    not the whole story; `attribution_notes` is where that messiness goes
    instead of being flattened away.
    """

    introduced: int | None = None
    original_authors: list[OriginalAuthor] = Field(default_factory=list)
    original_work: OriginalWork | None = None
    precursors: list[Precursor] = Field(default_factory=list)
    attribution_notes: str = ""


class Credits(BaseModel):
    """Who did the work *in Gigi*. Every entry is a `people.yaml` id, and the
    test suite fails on an id that does not resolve."""

    model_config = ConfigDict(populate_by_name=True)

    stewards: list[str] = Field(default_factory=list)
    spec_curators: list[str] = Field(default_factory=list)
    reference_implementation: list[str] = Field(default_factory=list)
    verifier_authors: list[str] = Field(default_factory=list)
    dataset_curators: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)
    adapter_contributors: dict[str, list[str]] = Field(default_factory=dict)

    def everyone(self) -> list[str]:
        """Every person id mentioned, deduplicated. Used to check attribution."""
        people = [
            *self.stewards,
            *self.spec_curators,
            *self.reference_implementation,
            *self.verifier_authors,
            *self.dataset_curators,
            *self.reviewers,
        ]
        for contributors in self.adapter_contributors.values():
            people.extend(contributors)
        return sorted(set(people))
