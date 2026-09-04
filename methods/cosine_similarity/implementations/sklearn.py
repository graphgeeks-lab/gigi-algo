"""Cosine similarity via scikit-learn's pairwise metrics.

`cosine_similarity(X)` returns the full n x n matrix, including the diagonal of
ones and both halves of every pair. Gigi's output is one score per unordered
pair, so the adapter takes the strict upper triangle -- see the `self_pairs`
and `pair_ordering` choice points, which are recorded precisely because this is
a decision rather than a fact.

scikit-learn reports 0.0 for a pair involving a zero vector, which is the
divergence `sklearn-cosine-zero-vector-is-zero`. Left alone when the policy is
unset; dropped when it is pinned to `undefined`. The zero rows are found from
the input rather than from the output, because a 0.0 in the result is
indistinguishable from a genuine orthogonal pair.
"""

from __future__ import annotations

from typing import Any

from gigi.vectors import pair_key


def run(converted, params: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    ids = converted.ids
    if len(ids) < 2:  # no pairs to score
        return {}, {"zero_vector_policy": params.get("zero_vector_policy"), "pairs": 0}

    matrix = cosine_similarity(converted.native)
    policy = params.get("zero_vector_policy")
    is_zero = [not np.any(row) for row in converted.native]

    scores: dict[str, float] = {}
    declined = 0
    for i, a in enumerate(ids):
        for j, b in enumerate(ids[i + 1:], start=i + 1):
            if policy == "undefined" and (is_zero[i] or is_zero[j]):
                declined += 1
                continue
            scores[pair_key(a, b)] = float(matrix[i][j])

    effective = {
        "zero_vector_policy": policy,
        "pairs_declined": declined,
        "matrix": "strict upper triangle of the full n x n result",
    }
    return scores, effective
