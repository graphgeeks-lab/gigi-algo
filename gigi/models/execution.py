"""What actually happened when something ran.

Requested versus effective parameters, per-backend results, the comparisons
between them, and the verification report that says whether the registry's
claims survived contact with reality.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from gigi.models.data import GraphProfile, VectorProfile
from gigi.models.spec import OutputKind


class RunStatus(str, Enum):
    ok = "ok"
    error = "error"
    unsupported = "unsupported"
    unavailable = "unavailable"


class ScoreResult(BaseModel):
    """One number per key.

    The key is a node id for `node_score` and a pair id like `a|b` for
    `similarity_score`. One model rather than two because the *comparison* is
    identical -- numeric tolerance over a matching key set -- and pretending
    otherwise would mean two comparators that must be kept in step.
    """

    # Constrained rather than the bare enum: a ScoreResult that claimed to be a
    # partition would be judged by the wrong comparator, and the union below
    # discriminates on exactly this.
    kind: Literal[OutputKind.node_score, OutputKind.similarity_score]
    score_name: str = "score"
    scores: dict[str, float]


class PartitionResult(BaseModel):
    """A grouping of keys, where the group *names* carry no meaning.

    `assignments` maps each key to its component label. The labels are
    canonical -- `c0`, `c1`, ... ordered by each component's smallest key --
    because the backends label components in four different and equally valid
    orders, and a result that is stable under reruns is worth more than one
    that preserves a backend's internal ordering.

    Canonicalising here does not make the comparator trivial by accident. It
    compares groupings, not labels, and would still catch two backends that
    genuinely disagreed about who belongs with whom. See
    `results.compare_partitions`.
    """

    kind: Literal[OutputKind.partition] = OutputKind.partition
    label_name: str = "component"
    assignments: dict[str, str]

    @property
    def component_count(self) -> int:
        return len(set(self.assignments.values()))

    def groups(self) -> frozenset[frozenset[str]]:
        """The partition as the mathematical object it is: a set of disjoint
        sets. This is what equality actually means here, and what the
        comparator uses."""
        buckets: dict[str, set[str]] = {}
        for key, label in self.assignments.items():
            buckets.setdefault(label, set()).add(key)
        return frozenset(frozenset(members) for members in buckets.values())

    def sizes(self) -> list[int]:
        """Component sizes, largest first. A cheap, label-free summary."""
        return sorted((len(g) for g in self.groups()), reverse=True)


# Every shape a run can produce. A plain union, discriminated by the `kind`
# literals above, so a stored run round-trips back into the right class.
NormalizedResult = ScoreResult | PartitionResult


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
    method_id: str
    # Which build produced this. Without it a stored run cannot be reproduced,
    # and it is what turns a RunResult into an experiment record.
    gigi_version: str = ""

    backend: str
    backend_version: str | None = None

    dataset_id: str | None = None
    # Whatever kind of thing it ran on. Named `profile` rather than
    # `graph_profile` now that not every input is a graph.
    profile: GraphProfile | VectorProfile | None = None

    # The whole point: what the caller asked for vs what the backend did.
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

    method_id: str
    dataset_id: str | None
    backend_a: str
    backend_b: str

    equivalent: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    absolute_tolerance: float
    notes: list[str] = Field(default_factory=list)


class Difference(BaseModel):
    """A cross-backend difference observed during verification.

    `divergence_id` is set when a registry entry already accounts for it. When
    it is None, the registry made a claim that reality does not support, and
    verification fails.
    """

    dataset_id: str | None
    backend_a: str
    backend_b: str
    metrics: dict[str, float] = Field(default_factory=dict)
    divergence_id: str | None = None
    detail: str = ""


class DivergenceCheck(BaseModel):
    """Whether a declared divergence still happens, on every fixture it names."""

    divergence_id: str
    datasets: list[str]
    backends: list[str]
    expected: Literal["differ", "match", "error"]
    observed: Literal["differ", "match", "error", "skipped"]
    reproduced: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    note: str = ""


class VerificationReport(BaseModel):
    """What happened when the registry's claims were checked against reality."""

    method_id: str
    gigi_version: str
    backends: list[str]
    backend_versions: dict[str, str | None] = Field(default_factory=dict)

    runs: list[RunResult] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)

    divergence_checks: list[DivergenceCheck] = Field(default_factory=list)
    explained_differences: list[Difference] = Field(default_factory=list)
    undeclared_differences: list[Difference] = Field(default_factory=list)

    status: Literal["pass", "fail"] = "pass"
    conclusion: str = ""
