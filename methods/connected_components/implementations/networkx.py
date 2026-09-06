"""Connected components via NetworkX.

Three functions for what Gigi treats as one method with a `mode`. The routing
matters: `nx.connected_components` raises `NetworkXNotImplemented` on a
directed graph rather than picking weak or strong for you, which is a defensible
refusal and the reason this adapter never calls it on one.

Returns an iterator of sets of node ids; Gigi's normaliser takes it as-is.
"""

from __future__ import annotations


def run(converted, params):
    import networkx as nx

    mode = params.get("mode") or "weak"
    directed = converted.directed

    if not directed:
        # On an undirected graph weak and strong coincide, and NetworkX has one
        # function for the case.
        function = nx.connected_components
    elif mode == "strong":
        function = nx.strongly_connected_components
    else:
        function = nx.weakly_connected_components

    components = [set(component) for component in function(converted.native)]

    effective = {
        "function": f"nx.{function.__name__}",
        "mode": mode if directed else "weak",
        "mode_applies": directed,
        "components": len(components),
    }
    # Sets of node ids.
    return components, effective
