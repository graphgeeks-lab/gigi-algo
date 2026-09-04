"""Cosine similarity via SciPy's condensed pairwise distances.

`pdist(X, metric="cosine")` returns cosine *distance*, one value per unordered
pair, in the same order Gigi builds `result_keys` -- (0,1), (0,2), ..., (1,2),
... -- so the mapping back to ids is a zip rather than a lookup.

SciPy returns NaN for a pair involving a zero vector, which is the divergence
`scipy-cosine-zero-vector-nan`. That is left alone when the policy is unset:
the whole point of the default is to show what the library does. Pinning the
policy to `undefined` drops those pairs so the backends can be compared on
everything else.
"""

from __future__ import annotations

import math
import warnings
from typing import Any


def run(converted, params: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    from scipy.spatial.distance import pdist

    keys = converted.result_keys
    if not keys:  # fewer than two vectors: no pairs to score
        return {}, {"zero_vector_policy": params.get("zero_vector_policy"), "pairs": 0}

    with warnings.catch_warnings():
        # The zero-vector division warns; the divergence entry is where that is
        # reported, and a warning here would only bury it.
        warnings.simplefilter("ignore")
        distances = pdist(converted.native, metric="cosine")

    scores = {key: 1.0 - float(value) for key, value in zip(keys, distances)}

    policy = params.get("zero_vector_policy")
    declined = 0
    if policy == "undefined":
        undefined = [key for key, value in scores.items() if not math.isfinite(value)]
        for key in undefined:
            del scores[key]
        declined = len(undefined)

    effective = {
        "zero_vector_policy": policy,
        "pairs_declined": declined,
        "metric": "cosine distance, subtracted from one",
    }
    return scores, effective
