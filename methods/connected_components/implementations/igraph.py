"""Connected components via python-igraph.

One function with a `mode`, which is the closest of the four backends to how
Gigi models this. It returns a `VertexClustering`, whose `.membership` is a
label per vertex in vertex order -- a membership vector rather than a list of
components, and the third shape Gigi's normaliser accepts.

igraph accepts `mode="strong"` on an undirected graph and returns the weak
answer. That is not a bug: on an undirected graph the two are the same
question. NetworkX and rustworkx refuse the same call, and the disagreement is
about strictness rather than about components -- recorded as a choice point in
method.yaml, not as a divergence.
"""

from __future__ import annotations


def run(converted, params):
    mode = params.get("mode") or "weak"
    applied = mode if converted.directed else "weak"

    clustering = converted.native.connected_components(mode=applied)
    membership = list(clustering.membership)

    effective = {
        "function": "ig.Graph.connected_components",
        "mode": applied,
        "mode_applies": converted.directed,
        "components": len(set(membership)),
    }
    # A label per vertex, in vertex order; Gigi maps it back to node ids.
    return membership, effective
