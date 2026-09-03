"""Every typed object Gigi passes between modules or writes to disk.

Deliberately one file. It splits when it passes ~400 lines, not before.
Nothing here imports another Gigi module, so it stays cheap to import.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------


class Maturity(str, Enum):
    """Controls how strictly CI treats an algorithm, and whether agents may
    select it without being asked."""

    stable = "stable"
    emerging = "emerging"
    frontier = "frontier"
    historical = "historical"


class OutputKind(str, Enum):
    """Semantic shape of a result. Comparison logic is chosen from this."""

    node_score = "node_score"
    node_component = "node_component"
    node_community = "node_community"
    path = "path"
    edge_score = "edge_score"
    graph_score = "graph_score"
    node_set = "node_set"


class Severity(str, Enum):
    """How much a divergence should worry a caller."""

    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DivergenceCategory(str, Enum):
    """What kind of difference it is. `default` and `semantic` are the two
    that change answers silently; the rest are usually visible."""

    default = "default"
    semantic = "semantic"
    numeric = "numeric"
    convergence = "convergence"
    graph_model = "graph_model"
    parameter = "parameter"
    output = "output"
    unsupported = "unsupported"
    bug = "bug"


class RunStatus(str, Enum):
    ok = "ok"
    error = "error"
    unsupported = "unsupported"
    unavailable = "unavailable"


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


# --------------------------------------------------------------------------
# Attribution
#
# Four questions that are routinely collapsed into one `inventor:` field, and
# should not be:
#
#   who created the algorithm  !=  who implemented it in Gigi
#                              !=  who verified it
#                              !=  who found the divergence
# --------------------------------------------------------------------------


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
    algorithm_id: str | None = None
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


# --------------------------------------------------------------------------
# Registry: what we claim about an algorithm
# --------------------------------------------------------------------------


class RequirementFlag(BaseModel):
    supported: bool
    preferred: bool | None = None
    notes: str | None = None


class Requirements(BaseModel):
    directed: RequirementFlag
    weighted: RequirementFlag
    negative_weights: RequirementFlag


class ParameterSpec(BaseModel):
    name: str
    type: Literal["float", "int", "str", "bool"]
    common_default: Any | None = None
    description: str = ""


class OutputSpec(BaseModel):
    kind: OutputKind
    score_name: str | None = None


class ComparisonSpec(BaseModel):
    """How two results of this algorithm are judged equivalent."""

    kind: Literal["numeric_vector", "partition", "path"]
    absolute_tolerance: float = 1e-6
    relative_tolerance: float = 1e-5


class DetectSpec(BaseModel):
    """Makes a divergence claim executable.

    The conformance suite runs `engines` on `dataset` with `parameters` and
    asserts the outcome equals `expect`. A divergence without a detect block is
    prose; a divergence with one is evidence.

    `engines` names exactly two, baseline first. `expect: error` asserts that
    the baseline runs and the second engine does not.

    `datasets` is a list because one difference often shows up on several
    fixtures, and splitting that into near-duplicate entries would make the
    registry harder to read rather than more precise. The claim reproduces only
    if it holds on every fixture named.
    """

    datasets: list[str]
    engines: list[str]
    parameters: dict[str, Any] = Field(default_factory=dict)
    expect: Literal["differ", "match", "error"] = "differ"


class Divergence(BaseModel):
    """One recorded difference between engines, and the evidence for it."""

    id: str
    category: DivergenceCategory
    severity: Severity
    engines: list[str]
    summary: str
    consequence: str = ""
    detect: DetectSpec | None = None

    # Finding a divergence is its own contribution, and a different one from
    # writing the spec or the adapter it was found in.
    discovered_by: list[str] = Field(default_factory=list)
    reported: str | None = None


class EngineSupport(BaseModel):
    supported: bool = True
    notes: str | None = None


class VerificationSettings(BaseModel):
    """Conditions under which engines are expected to agree.

    Verification pins every genuinely ambiguous parameter, so that a remaining
    disagreement is a semantic difference rather than a difference of defaults.
    Tolerances and iteration caps go here; `weight_property` is derived from
    the dataset.
    """

    parameters: dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    solves: list[str] = Field(default_factory=list)
    not_for: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Mathematics
#
# `maths.md` is exposition for people. This block is the same content in a form
# something other than a person can use: a reader that cannot parse prose still
# needs to know what the algorithm computes, what must be true of the answer,
# and where the definition leaves a choice open.
#
# See docs/adr/0008-machine-readable-first.md.
# --------------------------------------------------------------------------


class Formula(BaseModel):
    """One statement of the maths, in two registers.

    `statement` is plain text that renders anywhere. `latex` is for papers,
    typesetting, and any consumer that wants the real thing. Neither is
    optional in practice: an implementation that only has LaTeX cannot be read
    in a terminal, and one that only has plain text cannot be cited.
    """

    statement: str
    latex: str | None = None
    note: str | None = None


class Invariant(BaseModel):
    """A property the result must satisfy, checked on every run when possible.

    This is the cheapest useful form of the PROPERTY verifier: the maths says
    the scores sum to one, so every run asserts that the scores sum to one. A
    property that is written down but never checked is a comment.

    `id` must name a check in `gigi/invariants.py` when `check` is true.
    """

    id: str
    statement: str
    latex: str | None = None
    check: bool = True
    tolerance: float | None = None
    note: str | None = None


class ChoicePoint(BaseModel):
    """Somewhere the definition is under-determined.

    Divergences record where engines *did* differ; choice points record where
    they *could*. The first is measured, the second is derived from the maths,
    and having both means a new engine can be assessed before it is run.
    """

    id: str
    question: str
    choices: list[str] = Field(default_factory=list)
    note: str | None = None
    # The divergence this choice turned out to cause, if any, and the fixtures
    # that settle which answer the engines chose. A choice point with neither
    # is one nothing has tested yet -- which `gigi review` reports as a gap.
    divergence: str | None = None
    datasets: list[str] = Field(default_factory=list)


class Maths(BaseModel):
    """The machine-readable half of the mathematics. `maths.md` is the other."""

    summary: str = ""
    definition: Formula | None = None
    also: list[Formula] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    under_determined: list[ChoicePoint] = Field(default_factory=list)

    def checkable(self) -> list[Invariant]:
        return [invariant for invariant in self.invariants if invariant.check]


# --------------------------------------------------------------------------
# Relationships
# --------------------------------------------------------------------------


class RelationKind(str, Enum):
    """Typed edges between algorithms.

    `see_also` tells an agent nothing it can act on. "PageRank generalises
    eigenvector centrality, and they coincide when damping is 1 on a strongly
    connected graph" tells it when a substitution is legitimate.
    """

    generalizes = "generalizes"
    specializes = "specializes"
    equivalent_under = "equivalent_under"
    alternative_to = "alternative_to"
    builds_on = "builds_on"
    used_by = "used_by"
    dual_of = "dual_of"


# Kinds that must be mirrored on the other algorithm, and with what.
INVERSE_RELATIONS: dict[RelationKind, RelationKind] = {
    RelationKind.generalizes: RelationKind.specializes,
    RelationKind.specializes: RelationKind.generalizes,
    RelationKind.builds_on: RelationKind.used_by,
    RelationKind.used_by: RelationKind.builds_on,
    RelationKind.equivalent_under: RelationKind.equivalent_under,
    RelationKind.alternative_to: RelationKind.alternative_to,
    RelationKind.dual_of: RelationKind.dual_of,
}


class Relationship(BaseModel):
    kind: RelationKind
    algorithm: str
    condition: str | None = None
    note: str | None = None


class Family(BaseModel):
    """A record in `families/families.yaml`.

    A family is not a folder. It answers a question -- "in what order do I
    reach the nodes?", "which nodes hold the network together?" -- and an
    algorithm belongs to it when it answers that question.
    """

    id: str
    name: str
    question: str
    summary: str = ""
    parent: str | None = None
    related: list[str] = Field(default_factory=list)
    stewards: list[str] = Field(default_factory=list)


class Complexity(BaseModel):
    time: str | None = None
    space: str | None = None


class AlgorithmSpec(BaseModel):
    """Everything the registry claims about one algorithm.

    One file, `algorithms/<id>/algorithm.yaml`, and the only registration step
    there is. Grouped roughly as: identity, attribution, mathematics,
    requirements, output, engines, findings, relationships.
    """

    # `gigi:` in YAML reads better beside `provenance:`; `spec.credits` reads
    # better in Python. Both names work.
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    family: str
    maturity: Maturity

    problem: str
    provenance: Provenance = Field(default_factory=Provenance)
    credits: Credits = Field(default_factory=Credits, alias="gigi")
    intent: Intent = Field(default_factory=Intent)
    complexity: Complexity = Field(default_factory=Complexity)

    maths: Maths = Field(default_factory=Maths)

    requirements: Requirements
    parameters: list[ParameterSpec] = Field(default_factory=list)

    output: OutputSpec
    comparison: ComparisonSpec
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    deterministic: bool = True

    engines: dict[str, EngineSupport] = Field(default_factory=dict)
    divergences: list[Divergence] = Field(default_factory=list)

    relationships: list[Relationship] = Field(default_factory=list)

    datasets: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)

    def parameter(self, name: str) -> ParameterSpec | None:
        return next((p for p in self.parameters if p.name == name), None)

    def divergence(self, divergence_id: str) -> Divergence | None:
        return next((d for d in self.divergences if d.id == divergence_id), None)

    def related(self, kind: RelationKind) -> list[Relationship]:
        return [r for r in self.relationships if r.kind == kind]


# --------------------------------------------------------------------------
# Data: what we know about a graph
# --------------------------------------------------------------------------


class EdgeColumns(BaseModel):
    source: str = "source"
    target: str = "target"
    weight: str | None = None


class GraphMetadata(BaseModel):
    """`graph.yaml`: how to read a dataset, and what it should contain."""

    id: str
    description: str = ""
    directed: bool
    node_id: str = "id"
    edges: EdgeColumns = Field(default_factory=EdgeColumns)
    features: dict[str, bool] = Field(default_factory=dict)
    expected: dict[str, int] = Field(default_factory=dict)
    license: str = "CC0"


class GraphProfile(BaseModel):
    """Cheap facts only. Anything that is itself a graph algorithm (components,
    diameter, triangles, communities) is out of scope on purpose."""

    node_count: int
    edge_count: int

    directed: bool
    weighted: bool

    self_loop_count: int
    duplicate_edge_count: int
    dangling_node_count: int

    node_id_type: str
    weight_type: str | None = None
    has_negative_weights: bool | None = None

    degree_min: float | None = None
    degree_max: float | None = None
    degree_mean: float | None = None


# --------------------------------------------------------------------------
# Execution: what actually happened
# --------------------------------------------------------------------------


class NodeScoreResult(BaseModel):
    kind: Literal["node_score"] = "node_score"
    score_name: str = "score"
    scores: dict[str, float]


NormalizedResult = NodeScoreResult  # widened in v0.2 with components and paths


class InvariantResult(BaseModel):
    invariant_id: str
    statement: str
    passed: bool
    detail: str = ""


class RunResult(BaseModel):
    """One execution, fully described.

    Records requested and effective parameters separately, which is the whole
    point (ADR 0004), and is already an experiment row minus a candidate id.
    """

    run_id: str
    algorithm_id: str

    engine: str
    engine_version: str | None = None

    dataset_id: str | None = None
    graph_profile: GraphProfile | None = None

    # The whole point: what the caller asked for vs what the engine did.
    requested_parameters: dict[str, Any] = Field(default_factory=dict)
    effective_parameters: dict[str, Any] = Field(default_factory=dict)

    conversion_duration_ms: float = 0.0
    execution_duration_ms: float = 0.0
    normalization_duration_ms: float = 0.0

    status: RunStatus = RunStatus.ok
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)

    result: NormalizedResult | None = None
    invariants: list[InvariantResult] = Field(default_factory=list)

    @property
    def failed_invariants(self) -> list[InvariantResult]:
        return [i for i in self.invariants if not i.passed]

    @property
    def total_duration_ms(self) -> float:
        """Conversion plus execution plus normalisation."""
        return (
            self.conversion_duration_ms
            + self.execution_duration_ms
            + self.normalization_duration_ms
        )


class Comparison(BaseModel):
    """The verdict on two results of the same algorithm."""

    algorithm_id: str
    dataset_id: str | None
    engine_a: str
    engine_b: str

    equivalent: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    absolute_tolerance: float
    notes: list[str] = Field(default_factory=list)


class Difference(BaseModel):
    """A cross-engine difference observed during verification.

    `divergence_id` is set when a registry entry already accounts for it. When
    it is None, the registry made a claim that reality does not support, and
    verification fails.
    """

    dataset_id: str | None
    engine_a: str
    engine_b: str
    metrics: dict[str, float] = Field(default_factory=dict)
    divergence_id: str | None = None
    detail: str = ""


class DivergenceCheck(BaseModel):
    """Whether a declared divergence still happens, on every fixture it names."""

    divergence_id: str
    datasets: list[str]
    engines: list[str]
    expected: Literal["differ", "match", "error"]
    observed: Literal["differ", "match", "error", "skipped"]
    reproduced: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    note: str = ""


class VerificationReport(BaseModel):
    """What happened when the registry's claims were checked against reality."""

    algorithm_id: str
    gigi_version: str
    engines: list[str]
    engine_versions: dict[str, str | None] = Field(default_factory=dict)

    runs: list[RunResult] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)

    divergence_checks: list[DivergenceCheck] = Field(default_factory=list)
    explained_differences: list[Difference] = Field(default_factory=list)
    undeclared_differences: list[Difference] = Field(default_factory=list)

    status: Literal["pass", "fail"] = "pass"
    conclusion: str = ""
