"""Normalisation and semantic comparison.

`gigi compare` must never mean raw equality. Two engines can be identically
correct and still return different bytes -- different key types, different
orderings, floating point noise from different convergence strategies. What
counts as "the same answer" depends on the output family, so it is declared in
`algorithm.yaml` and implemented here.

v0.1 implements `node_score` only. Partitions (components, communities) and
paths arrive in v0.2 alongside the algorithms that need them.
"""

from __future__ import annotations

from typing import Any, Sequence

from gigi.models import AlgorithmSpec, Comparison, NodeScoreResult


class NormalizationError(Exception):
    pass


def normalize_node_score(
    payload: Any,
    node_ids: Sequence[str],
    score_name: str = "score",
) -> NodeScoreResult:
    """Accept the three shapes engines naturally return.

    - a mapping keyed by canonical node id      (networkx, reference)
    - a mapping keyed by node index             (rustworkx)
    - a sequence positionally aligned with nodes (igraph)

    Doing the mapping here rather than in each implementation file is what
    keeps `implementations/<engine>.py` down to a dozen lines.
    """
    if isinstance(payload, dict):
        keys = list(payload.keys())
        if keys and all(isinstance(k, int) for k in keys):
            scores = {str(node_ids[k]): float(v) for k, v in payload.items()}
        else:
            scores = {str(k): float(v) for k, v in payload.items()}
    elif isinstance(payload, (list, tuple)):
        if len(payload) != len(node_ids):
            raise NormalizationError(
                f"engine returned {len(payload)} scores for {len(node_ids)} nodes"
            )
        scores = {str(node): float(value) for node, value in zip(node_ids, payload)}
    else:
        raise NormalizationError(f"cannot normalize result of type {type(payload)!r}")

    missing = set(map(str, node_ids)) - set(scores)
    if missing:
        raise NormalizationError(
            f"engine returned no score for {len(missing)} node(s): "
            f"{sorted(missing)[:5]}"
        )
    return NodeScoreResult(score_name=score_name, scores=scores)


def compare_node_scores(
    a: NodeScoreResult,
    b: NodeScoreResult,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[bool, dict[str, float], list[str]]:
    """Compare two score vectors element-wise.

    Returns (equivalent, metrics, notes). Equivalence uses the usual
    `|a - b| <= atol + rtol * |b|` per element, so a large score and a tiny
    one are held to appropriately different standards.
    """
    notes: list[str] = []

    only_a = sorted(set(a.scores) - set(b.scores))
    only_b = sorted(set(b.scores) - set(a.scores))
    if only_a or only_b:
        notes.append(
            f"node sets differ: {len(only_a)} only in first, {len(only_b)} only in second"
        )
        return False, {}, notes

    if not a.scores:
        return True, {"max_abs_error": 0.0, "mean_abs_error": 0.0, "max_rel_error": 0.0}, notes

    abs_errors = []
    rel_errors = []
    within = True
    for node, value_a in a.scores.items():
        value_b = b.scores[node]
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
        "top_node_agrees": float(_argmax(a.scores) == _argmax(b.scores)),
    }
    return within, metrics, notes


def _argmax(scores: dict[str, float]) -> str:
    # Ties broken by node id so the metric is deterministic.
    return max(sorted(scores), key=lambda node: scores[node])


def compare_results(
    spec: AlgorithmSpec,
    dataset_id: str | None,
    engine_a: str,
    result_a: NodeScoreResult,
    engine_b: str,
    result_b: NodeScoreResult,
) -> Comparison:
    """Dispatch on the comparison kind declared in `algorithm.yaml`."""
    if spec.comparison.kind != "numeric_vector":
        raise NormalizationError(
            f"comparison kind {spec.comparison.kind!r} is not implemented in v0.1"
        )

    equivalent, metrics, notes = compare_node_scores(
        result_a,
        result_b,
        spec.comparison.absolute_tolerance,
        spec.comparison.relative_tolerance,
    )
    return Comparison(
        algorithm_id=spec.id,
        dataset_id=dataset_id,
        engine_a=engine_a,
        engine_b=engine_b,
        equivalent=equivalent,
        metrics=metrics,
        absolute_tolerance=spec.comparison.absolute_tolerance,
        notes=notes,
    )
