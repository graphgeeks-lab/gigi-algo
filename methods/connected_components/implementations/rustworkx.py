"""Connected components via rustworkx.

Three functions again, and a stricter type system behind them:
`rx.strongly_connected_components` takes a `PyDiGraph` and raises `TypeError`
on an undirected `PyGraph` rather than answering. So the same routing NetworkX
needs is needed here, for a different reason.

Returns sets or lists of *node indices*, not ids. Gigi's normaliser maps them
back through the converted graph's node order, which is why that order is part
of the adapter contract.
"""

from __future__ import annotations


def run(converted, params):
    import rustworkx as rx

    mode = params.get("mode") or "weak"
    directed = converted.directed

    if not directed:
        function = rx.connected_components
    elif mode == "strong":
        function = rx.strongly_connected_components
    else:
        function = rx.weakly_connected_components

    components = [set(component) for component in function(converted.native)]

    effective = {
        "function": f"rx.{function.__name__}",
        "mode": mode if directed else "weak",
        "mode_applies": directed,
        "components": len(components),
    }
    # Sets of node indices; Gigi maps them back to node ids.
    return components, effective
