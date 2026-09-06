"""Cosine similarity, written to be read.

    cos(x, y) = <x, y> / (||x|| ||y||)

One dot product and two norms per pair, in plain Python. This is the oracle
every other backend is compared against, so it optimises for being obviously
correct rather than for being fast -- O(n^2 d) with no attempt to hide it. See
ADR 0002.

The zero vector is the whole story here. A vector of all zeros has no
direction, so the angle to it does not exist and the definition simply does not
say what to return. This implementation declines the pair, and says so in its
effective parameters, rather than inventing a number the way both libraries do.
"""

from __future__ import annotations

import math
from typing import Any

from gigi.vectors import pair_key

# The reference's answer where the definition has none: leave the pair out.
# Named rather than inlined because it is a decision, not a detail.
DECLINE = "undefined"


def dot(x: list[float], y: list[float]) -> float:
    return math.fsum(a * b for a, b in zip(x, y))


def norm(x: list[float]) -> float:
    return math.sqrt(dot(x, x))


def run(converted, params: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    """Every unordered pair of distinct vectors, keyed `a|b` with a < b."""
    rows: dict[str, list[float]] = converted.native
    ids = converted.ids

    policy = params.get("zero_vector_policy") or DECLINE
    norms = {name: norm(vector) for name, vector in rows.items()}

    scores: dict[str, float] = {}
    declined = 0
    for index, a in enumerate(ids):
        for b in ids[index + 1:]:
            if norms[a] == 0.0 or norms[b] == 0.0:
                if policy == "zero":
                    scores[pair_key(a, b)] = 0.0
                else:
                    declined += 1
                continue
            scores[pair_key(a, b)] = dot(rows[a], rows[b]) / (norms[a] * norms[b])

    effective = {
        "zero_vector_policy": policy,
        "pairs_declined": declined,
        "source": "gigi reference implementation",
    }
    return scores, effective
