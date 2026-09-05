"""What the registry claims about a method: the whole of `method.yaml`.

The largest of these modules because it is the interesting one. Grouped in the
order a reader meets it: identity and taxonomy, what it consumes and produces,
the mathematics, what backends do with it, and how it relates to everything
else.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from gigi.models.people import Credits, Provenance


class Maturity(str, Enum):
    """Controls how strictly CI treats an algorithm, and whether agents may
    select it without being asked."""

    stable = "stable"
    emerging = "emerging"
    frontier = "frontier"
    historical = "historical"


class MethodKind(str, Enum):
    """What sort of thing this is.

    PageRank is an algorithm, cosine similarity is a measure, Fellegi-Sunter is
    a statistical model. The distinction is not cosmetic: it changes what
    verifying the thing even means, so it is carried rather than inferred.
    """

    algorithm = "algorithm"
    measure = "measure"
    statistical_model = "statistical_model"
    heuristic = "heuristic"
    procedure = "procedure"
    solver = "solver"


class InputKind(str, Enum):
    """What a method consumes. The discriminator for `InputSpec`."""

    graph = "graph"
    vectors = "vectors"


class OutputKind(str, Enum):
    """Semantic shape of a result, and the comparator that judges it.

    Deliberately short. A kind here without an entry in `results.COMPARATORS`
    would describe a method nothing can verify, so the test suite refuses one
    -- the same rule as an invariant that names no check.

    `node_score` and `similarity_score` share a comparator, and that is not a
    shortcut: both are one number per key, judged by numeric tolerance over a
    matching key set. What differs is what the key *means* -- a node, or a pair
    of things being compared.

    `partition` does not, and could not: two partitions are the same answer when
    they induce the same grouping, whatever the components are *called*. Every
    backend labels them differently -- igraph counts in reverse topological
    order, rustworkx in reverse index order -- and comparing labels would report
    four correct implementations as four different answers. Paths need a third
    comparator and arrive with the method that produces them.
    """

    node_score = "node_score"
    similarity_score = "similarity_score"
    partition = "partition"


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


class AiContext(BaseModel):
    """Guidance for a reader that is not a person.

    Deliberately Apache OSSIE's shape, field for field, so anything that
    already consumes an OSSIE `ai_context` consumes ours without special
    casing. OSSIE describes what *data* means; this describes what a *method*
    means; the two halves are what a semantic conflict check needs. Copied
    rather than imported -- see docs/ONTOLOGY.md.
    """

    instructions: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class Intent(BaseModel):
    """What a method is, and is not, for.

    `not_for` names *problems*, not free text, so that `gigi why` can print the
    questions this method does not answer rather than a vague disclaimer.
    """

    not_for: list[str] = Field(default_factory=list)


class ProblemSpec(BaseModel):
    """A record in `problems/<id>.yaml`: a question, independent of any method.

    Problems exist so that "which method should I use?" has somewhere to start
    that is not a method name. A method solves problems; the problems it is
    commonly mistaken for are named too, because that is the more useful half
    of the answer.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    domain: str
    question: str
    description: str = ""
    input_kinds: list[InputKind] = Field(default_factory=list)
    output_kinds: list[OutputKind] = Field(default_factory=list)
    related_problems: list[str] = Field(default_factory=list)
    ai_context: AiContext | None = None


class RequirementFlag(BaseModel):
    supported: bool
    preferred: bool | None = None
    notes: str | None = None


class GraphInputSpec(BaseModel):
    """A method that consumes a graph."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["graph"] = "graph"

    directed: RequirementFlag
    weighted: RequirementFlag
    negative_weights: RequirementFlag

    multigraph: RequirementFlag | None = None
    node_attributes: list[str] = Field(default_factory=list)
    edge_attributes: list[str] = Field(default_factory=list)


class VectorInputSpec(BaseModel):
    """A method that consumes vectors -- cosine similarity and its neighbours.

    Written in PR 1 so the union was genuinely discriminated before anything
    depended on it, and filled in by PR 2b when cosine similarity arrived. The
    flags are the ones a caller has to know before handing over data: whether
    the values must be numeric, whether a sparse representation is accepted,
    and what happens to a vector with no direction.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["vectors"] = "vectors"

    numeric: bool = True
    sparse: RequirementFlag | None = None
    zero_vectors: RequirementFlag | None = None
    same_length_required: bool = True


InputSpec = Annotated[GraphInputSpec | VectorInputSpec, Field(discriminator="kind")]


class ParameterInterpretation(BaseModel):
    """What a larger value of this parameter *means* to the method."""

    higher_means: str | None = None
    note: str | None = None


class ParameterSpec(BaseModel):
    """One knob, what it does, and what a larger value *means*."""

    name: str
    type: Literal["float", "int", "str", "bool"]
    common_default: Any | None = None
    description: str = ""

    # The same column can be the right input to two methods and mean opposite
    # things to them. PageRank reads edge weight as `strength` (higher is a
    # stronger transition); Dijkstra reads it as `cost` (higher is worse). A
    # user whose column holds *distance* and who runs both has asked two
    # contradictory questions and been told nothing. This is the field that
    # lets `gigi why` notice.
    semantic_role: str | None = None
    interpretation: ParameterInterpretation | None = None
    ai_context: AiContext | None = None


class OutputSpec(BaseModel):
    """What the method produces, and what to call it.

    `score_name` names the number for the score kinds; `label_name` names the
    group for `partition`. Two fields rather than one generic `value_name`
    because "the pagerank score" and "the component" are what a reader expects
    to see in a column header, and one field would have to be documented as
    meaning different things.
    """

    kind: OutputKind
    score_name: str | None = None
    label_name: str | None = None


class ComparisonSpec(BaseModel):
    """How close two results have to be to count as the same answer.

    Which comparator runs is decided by `output.kind`, not restated here: two
    fields naming one fact is how a registry starts contradicting itself.
    """

    absolute_tolerance: float = 1e-6
    relative_tolerance: float = 1e-5


class DetectSpec(BaseModel):
    """Makes a divergence claim executable.

    The conformance suite runs `backends` on `dataset` with `parameters` and
    asserts the outcome equals `expect`. A divergence without a detect block is
    prose; a divergence with one is evidence.

    `backends` names exactly two, baseline first. `expect: error` asserts that
    the baseline runs and the second backend does not.

    `datasets` is a list because one difference often shows up on several
    fixtures, and splitting that into near-duplicate entries would make the
    registry harder to read rather than more precise. The claim reproduces only
    if it holds on every fixture named.
    """

    datasets: list[str]
    backends: list[str]
    parameters: dict[str, Any] = Field(default_factory=dict)
    expect: Literal["differ", "match", "error"] = "differ"


class Divergence(BaseModel):
    """One recorded difference between backends, and the evidence for it."""

    id: str
    category: DivergenceCategory
    severity: Severity
    backends: list[str]
    summary: str
    consequence: str = ""
    detect: DetectSpec | None = None

    # Finding a divergence is its own contribution, and a different one from
    # writing the spec or the adapter it was found in.
    discovered_by: list[str] = Field(default_factory=list)
    reported: str | None = None


class BackendSupport(BaseModel):
    supported: bool = True
    notes: str | None = None


class VerificationSettings(BaseModel):
    """Conditions under which backends are expected to agree.

    Verification pins every genuinely ambiguous parameter, so that a remaining
    disagreement is a semantic difference rather than a difference of defaults.
    Tolerances and iteration caps go here; `weight_property` is derived from
    the dataset.
    """

    parameters: dict[str, Any] = Field(default_factory=dict)


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

    Divergences record where backends *did* differ; choice points record where
    they *could*. The first is measured, the second is derived from the maths,
    and having both means a new backend can be assessed before it is run.
    """

    id: str
    question: str
    choices: list[str] = Field(default_factory=list)
    note: str | None = None
    # The divergences this choice turned out to cause, if any, and the fixtures
    # that settle which answer the backends chose. A choice point with neither
    # is one nothing has tested yet -- which `gigi review` reports as a gap.
    divergences: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)


class InlineGraph(BaseModel):
    """A graph small enough to write in a test case by hand.

    `edges` are `[source, target]` or `[source, target, weight]`. `nodes` is
    only needed for nodes with no edges.
    """

    directed: bool = True
    edges: list[list[Any]] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)


class InlineVectors(BaseModel):
    """Vectors small enough to write in a test case by hand.

    Keyed by id, each a list of numbers of the same length. The vector
    equivalent of `InlineGraph`, and there for the same reason: the cases
    that pin a definition are usually smaller than any fixture worth
    keeping on disk.
    """

    rows: dict[str, list[float]]


class KnownAnswer(BaseModel):
    """One case in `methods/<id>/tests/expected.yaml`.

    The point is `derived`: it says where the expected answer came from, and
    it must not be "I ran the code". A known answer obtained by symmetry, a
    closed form, a hand calculation or a paper is an independent check on the
    reference implementation -- the only one the oracle gets.
    """

    id: str
    description: str = ""
    derived: str
    dataset: str | None = None
    graph: InlineGraph | None = None
    vectors: InlineVectors | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    # Keyed the way the method's output is keyed: by node for a node score,
    # by canonical pair (`a|b`) for a similarity score.
    expected: dict[str, float] = Field(default_factory=dict)
    # For a `partition`, where the expected answer is a grouping and the group
    # *names* are meaningless. Written as a list of lists, in any order, with
    # members in any order -- exactly as loosely as the maths allows, so a case
    # cannot accidentally assert something the definition does not say.
    expected_components: list[list[str]] | None = None
    tolerance: float = 1e-9

    def expects_a_partition(self) -> bool:
        return self.expected_components is not None

    def data(self) -> str | InlineGraph | InlineVectors | None:
        """Whatever this case is to be run on. Exactly one is set."""
        return self.dataset or self.graph or self.vectors


class Maths(BaseModel):
    """The machine-readable half of the mathematics. `maths.md` is the other."""

    summary: str = ""
    definition: Formula | None = None
    also: list[Formula] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    under_determined: list[ChoicePoint] = Field(default_factory=list)

    def checkable(self) -> list[Invariant]:
        return [invariant for invariant in self.invariants if invariant.check]


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


# Kinds that must be mirrored on the other method, and with what.
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
    method: str
    condition: str | None = None
    note: str | None = None


class DomainMeaning(BaseModel):
    """A real-world meaning a value might carry, and how well it fits.

    `dangerous` does not mean forbidden. It means the method will happily
    compute an answer to a question the user did not ask.
    """

    meaning: str
    fit: Literal["strong", "contextual", "dangerous"]
    note: str | None = None


class SemanticInterpretation(BaseModel):
    """How this method reads one part of its input.

    The registry's answer to "what does this number mean to you?", which is
    half of a conflict check. The other half is what the number means in the
    user's data -- inferred from the column, or read from an OSSIE semantic
    model.
    """

    id: str
    subject: str
    semantic_role: str
    description: str = ""
    higher_means: str | None = None
    common_domain_meanings: list[DomainMeaning] = Field(default_factory=list)


class UseCaseSpec(BaseModel):
    """A real situation, and what the method means once mapped onto it.

    Structured rather than a sentence, because `input_mapping` is the part
    that goes wrong: the moment `weight` becomes `transaction_amount`, the
    method is answering a different question, and `cautions` is where that is
    said out loud.
    """

    id: str
    domain: str
    question: str
    input_mapping: dict[str, str] = Field(default_factory=dict)
    method_semantics: str = ""
    cautions: list[str] = Field(default_factory=list)
    related_methods: list[str] = Field(default_factory=list)


class DomainSpec(BaseModel):
    """A record in `domains/domains.yaml`.

    The widest grouping: graph, similarity, entity_resolution, geospatial. A
    domain earns its place by having at least one family in it -- an empty
    domain is a plan, not a fact, and the test suite says so.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    related: list[str] = Field(default_factory=list)


class Family(BaseModel):
    """A record in `families/families.yaml`.

    A family is not a folder. It answers a question -- "in what order do I
    reach the nodes?", "which nodes hold the network together?" -- and an
    algorithm belongs to it when it answers that question.
    """

    id: str
    name: str
    domain: str
    question: str
    summary: str = ""
    parent: str | None = None
    related: list[str] = Field(default_factory=list)
    stewards: list[str] = Field(default_factory=list)


class Complexity(BaseModel):
    time: str | None = None
    space: str | None = None


class MethodSpec(BaseModel):
    """Everything the registry claims about one algorithm.

    One file, `methods/<id>/method.yaml`, and the only registration step
    there is. Grouped roughly as: identity, attribution, mathematics,
    requirements, output, backends, findings, relationships.
    """

    # `gigi:` in YAML reads better beside `provenance:`; `spec.credits` reads
    # better in Python. Both names work.
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    kind: MethodKind
    aliases: list[str] = Field(default_factory=list)
    # A method belongs to a family, and the family belongs to a domain. The
    # domain is therefore *derived* (`registry.domain_of`) rather than stored:
    # one fact, one place.
    family: str
    maturity: Maturity

    # One line on what this method does. The *questions* it answers live in
    # `problems`, as ids into problems/.
    summary: str
    problems: list[str] = Field(default_factory=list)

    provenance: Provenance = Field(default_factory=Provenance)
    credits: Credits = Field(default_factory=Credits, alias="gigi")
    intent: Intent = Field(default_factory=Intent)
    complexity: Complexity = Field(default_factory=Complexity)

    maths: Maths = Field(default_factory=Maths)

    inputs: list[InputSpec]
    parameters: list[ParameterSpec] = Field(default_factory=list)

    output: OutputSpec
    comparison: ComparisonSpec
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    deterministic: bool = True

    backends: dict[str, BackendSupport] = Field(default_factory=dict)
    divergences: list[Divergence] = Field(default_factory=list)

    relationships: list[Relationship] = Field(default_factory=list)
    semantic_interpretations: list[SemanticInterpretation] = Field(default_factory=list)

    datasets: list[str] = Field(default_factory=list)
    use_cases: list[UseCaseSpec] = Field(default_factory=list)
    ai_context: AiContext | None = None

    def parameter(self, name: str) -> ParameterSpec | None:
        return next((p for p in self.parameters if p.name == name), None)

    def divergence(self, divergence_id: str) -> Divergence | None:
        return next((d for d in self.divergences if d.id == divergence_id), None)

    def related(self, kind: RelationKind) -> list[Relationship]:
        return [r for r in self.relationships if r.kind == kind]
