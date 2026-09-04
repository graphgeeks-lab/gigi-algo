"""Normalisation and semantic comparison.

`gigi compare` must never mean raw equality. Two backends can be identically
correct and still return different bytes -- different key types, different
orderings, floating point noise from different convergence strategies. What
counts as "the same answer" depends on the output family, so it is declared in
`method.yaml` and implemented here.

Three output kinds. `node_score` and `similarity_score` are one number per key
and share a comparator. `partition` is a grouping, and needs its own: two
partitions are the same answer when they induce the same grouping, whatever the
components happen to be called. Paths need a third and arrive with the method
that produces them.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from gigi.models import (
    Comparison,
    MethodSpec,
    OutputSpec,
    NormalizedResult,
    OutputKind,
    PartitionResult,
    ScoreResult,
)


class NormalizationError(Exception):
    pass


def normalize_scores(
    payload: Any,
    keys: Sequence[str],
    kind: OutputKind,
    score_name: str = "score",
    require_all_keys: bool = True,
) -> ScoreResult:
    """Accept the three shapes backends naturally return.

    - a mapping keyed by canonical id            (networkx, reference, sklearn)
    - a mapping keyed by index                   (rustworkx)
    - a sequence positionally aligned with keys  (igraph)

    Doing the mapping here rather than in each implementation file is what
    keeps `implementations/<backend>.py` down to a dozen lines.

    `require_all_keys` is False where a method may legitimately decline a key --
    a similarity measure asked about a zero vector, say. The comparator still
    notices when two backends decline different ones.
    """
    if isinstance(payload, dict):
        payload_keys = list(payload.keys())
        if payload_keys and all(isinstance(k, int) for k in payload_keys):
            scores = {str(keys[k]): float(v) for k, v in payload.items()}
        else:
            scores = {str(k): float(v) for k, v in payload.items()}
    elif isinstance(payload, (list, tuple)):
        if len(payload) != len(keys):
            raise NormalizationError(
                f"backend returned {len(payload)} scores for {len(keys)} keys"
            )
        scores = {str(key): float(value) for key, value in zip(keys, payload)}
    else:
        raise NormalizationError(f"cannot normalize result of type {type(payload)!r}")

    if require_all_keys:
        missing = set(map(str, keys)) - set(scores)
        if missing:
            raise NormalizationError(
                f"backend returned no score for {len(missing)} key(s): "
                f"{sorted(missing)[:5]}"
            )
    return ScoreResult(kind=kind, score_name=score_name, scores=scores)


def normalize_partition(
    payload: Any,
    keys: Sequence[str],
    label_name: str = "component",
    require_all_keys: bool = True,
) -> PartitionResult:
    """Accept the three shapes backends return a grouping in.

    - a sequence of collections, one per component  (networkx, rustworkx)
    - a flat membership sequence aligned with keys  (igraph)
    - a mapping from key, or key index, to a label

    Members may be canonical ids or integer indices into `keys`; both appear in
    practice and neither is worth pushing back into the implementation files.

    Labels are rewritten to `c0`, `c1`, ... ordered by where each component's
    earliest member sits in `keys`. Backends label components in four different
    orders -- none of which the definition says anything about -- so preserving
    a backend's labels would record an arbitrary choice as if it were an answer.
    """
    groups = _as_groups(payload, keys)

    seen: dict[str, int] = {}
    for index, members in enumerate(groups):
        for key in members:
            if key in seen:
                raise NormalizationError(
                    f"key {key!r} is in two components ({seen[key]} and {index}); "
                    f"a partition cannot overlap"
                )
            seen[key] = index

    unknown = sorted(set(seen) - set(map(str, keys)))
    if unknown:
        raise NormalizationError(
            f"backend put {len(unknown)} unknown key(s) in a component: {unknown[:5]}"
        )
    if require_all_keys:
        missing = set(map(str, keys)) - set(seen)
        if missing:
            raise NormalizationError(
                f"backend assigned no component to {len(missing)} key(s): "
                f"{sorted(missing)[:5]}"
            )

    position = {key: index for index, key in enumerate(map(str, keys))}
    ordered = sorted(groups, key=lambda members: min(position[k] for k in members))
    assignments = {
        key: f"c{index}"
        for index, members in enumerate(ordered)
        for key in sorted(members, key=lambda k: position[k])
    }
    return PartitionResult(label_name=label_name, assignments=assignments)


def _as_groups(payload: Any, keys: Sequence[str]) -> list[set[str]]:
    """Whatever the backend returned, as a list of sets of canonical ids."""

    def name(member: Any) -> str:
        """One member as a canonical id. An integer is an index into `keys`,
        which is how igraph and rustworkx refer to nodes."""
        if isinstance(member, int) and not isinstance(member, bool):
            try:
                return str(keys[member])
            except IndexError:
                raise NormalizationError(
                    f"backend referred to index {member}, but there are "
                    f"{len(keys)} keys"
                ) from None
        return str(member)

    if isinstance(payload, dict):
        # key -> label, or index -> label.
        buckets: dict[str, set[str]] = {}
        for member, label in payload.items():
            buckets.setdefault(str(label), set()).add(name(member))
        return list(buckets.values())

    if not isinstance(payload, (list, tuple)):
        raise NormalizationError(f"cannot normalize a partition of type {type(payload)!r}")

    # A sequence of collections is a list of components; a flat sequence is a
    # membership vector. Nothing else is a partition.
    if payload and all(isinstance(item, (set, frozenset, list, tuple)) for item in payload):
        return [{name(member) for member in component} for component in payload]

    if not payload:
        return []

    if len(payload) != len(keys):
        raise NormalizationError(
            f"membership vector has {len(payload)} entries for {len(keys)} keys"
        )
    memberships: dict[str, set[str]] = {}
    for key, label in zip(map(str, keys), payload):
        memberships.setdefault(str(label), set()).add(key)
    return list(memberships.values())


def compare_partitions(
    a: PartitionResult,
    b: PartitionResult,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[bool, dict[str, float], list[str]]:
    """Compare two groupings, ignoring what the components are called.

    Tolerances are accepted to match the comparator signature and then ignored,
    deliberately: there is no such thing as approximately the same partition.
    Two nodes are in the same component or they are not.
    """
    notes: list[str] = []

    only_a = sorted(set(a.assignments) - set(b.assignments))
    only_b = sorted(set(b.assignments) - set(a.assignments))
    if only_a or only_b:
        notes.append(
            f"key sets differ: {len(only_a)} only in first, {len(only_b)} only in second"
        )
        return False, {}, notes

    groups_a, groups_b = a.groups(), b.groups()
    metrics = {
        "components_a": float(len(groups_a)),
        "components_b": float(len(groups_b)),
        "largest_component_a": float(a.sizes()[0]) if groups_a else 0.0,
        "largest_component_b": float(b.sizes()[0]) if groups_b else 0.0,
    }
    if groups_a == groups_b:
        metrics["keys_grouped_differently"] = 0.0
        return True, metrics, notes

    # Which keys actually landed among different company. Reported rather than
    # a count of differing labels, because labels are not the property.
    company_a = {key: frozenset(g) for g in groups_a for key in g}
    company_b = {key: frozenset(g) for g in groups_b for key in g}
    moved = sorted(key for key in company_a if company_a[key] != company_b[key])
    metrics["keys_grouped_differently"] = float(len(moved))
    notes.append(
        f"{len(moved)} key(s) grouped differently, e.g. {moved[:5]}; "
        f"{len(groups_a)} component(s) vs {len(groups_b)}"
    )
    return False, metrics, notes


def normalize(
    payload: Any,
    keys: Sequence[str],
    output: "OutputSpec",
    require_all_keys: bool = True,
) -> NormalizedResult:
    """Turn whatever a backend returned into the shape its output kind names.

    The harness calls this and nothing else, so adding an output kind means
    adding a normaliser and a comparator here -- never a branch in `run`.
    """
    if output.kind is OutputKind.partition:
        return normalize_partition(
            payload, keys, output.label_name or "component", require_all_keys
        )
    return normalize_scores(
        payload, keys, output.kind, output.score_name or "score", require_all_keys
    )


def compare_scores(
    a: ScoreResult,
    b: ScoreResult,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[bool, dict[str, float], list[str]]:
    """Compare two score vectors element-wise.

    Returns (equivalent, metrics, notes). Equivalence uses the usual
    `|a - b| <= atol + rtol * |b|` per element, so a large score and a tiny
    one are held to appropriately different standards.
    """
    notes: list[str] = []

    # A key set that differs is a real answer, not a precondition failure: two
    # backends can disagree about *whether a pair has an answer at all*, which
    # is exactly what a zero vector does to a cosine.
    only_a = sorted(set(a.scores) - set(b.scores))
    only_b = sorted(set(b.scores) - set(a.scores))
    if only_a or only_b:
        notes.append(
            f"key sets differ: {len(only_a)} only in first, {len(only_b)} only in second"
        )
        return False, {}, notes

    if not a.scores:
        return True, {"max_abs_error": 0.0, "mean_abs_error": 0.0, "max_rel_error": 0.0}, notes

    abs_errors = []
    rel_errors = []
    within = True
    for key, value_a in a.scores.items():
        value_b = b.scores[key]
        # A non-finite score can never be equivalent to anything: NaN compares
        # False against every threshold, which would otherwise make it pass.
        # This is how a rustworkx NaN was first caught, so it stays explicit.
        if not (math.isfinite(value_a) and math.isfinite(value_b)):
            within = False
            notes.append(f"{key}: non-finite score ({value_a!r} vs {value_b!r})")
            abs_errors.append(math.inf)
            rel_errors.append(math.inf)
            continue
        abs_error = abs(value_a - value_b)
        abs_errors.append(abs_error)
        denominator = max(abs(value_a), abs(value_b))
        rel_errors.append(abs_error / denominator if denominator else 0.0)
        if abs_error > absolute_tolerance + relative_tolerance * abs(value_b):
            within = False

    metrics = {
        "max_abs_error": max(abs_errors),
        "mean_abs_error": sum(abs_errors) / len(abs_errors),
        "max_rel_error": max(rel_errors),
        "top_key_agrees": float(_argmax(a.scores) == _argmax(b.scores)),
    }
    return within, metrics, notes


def _argmax(scores: dict[str, float]) -> str:
    # Ties broken by key so the metric is deterministic.
    return max(sorted(scores), key=lambda key: scores[key])


# Every output kind, and the comparator that judges it. A kind absent from
# here describes a method nothing can verify, which `tests/test_results.py`
# refuses -- the same rule as an invariant that names no check.
COMPARATORS = {
    OutputKind.node_score: compare_scores,
    # The same comparator, deliberately: both are one number per key, judged by
    # numeric tolerance over a matching key set. Only the meaning of the key
    # differs -- a node, or a pair of things being compared.
    OutputKind.similarity_score: compare_scores,
    # A different one, necessarily. See compare_partitions.
    OutputKind.partition: compare_partitions,
}


def compare_results(
    spec: MethodSpec,
    dataset_id: str | None,
    backend_a: str,
    result_a: NormalizedResult,
    backend_b: str,
    result_b: NormalizedResult,
) -> Comparison:
    """Judge two results, using the comparator for this method's output kind."""
    comparator = COMPARATORS.get(spec.output.kind)
    if comparator is None:
        raise NormalizationError(
            f"output kind {spec.output.kind.value!r} has no comparator in "
            f"gigi/results.py (known: {', '.join(k.value for k in COMPARATORS)})"
        )

    equivalent, metrics, notes = comparator(
        result_a,
        result_b,
        spec.comparison.absolute_tolerance,
        spec.comparison.relative_tolerance,
    )
    return Comparison(
        method_id=spec.id,
        dataset_id=dataset_id,
        backend_a=backend_a,
        backend_b=backend_b,
        equivalent=equivalent,
        metrics=metrics,
        absolute_tolerance=spec.comparison.absolute_tolerance,
        notes=notes,
    )
