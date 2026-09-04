"""Connected components, written to be read.

A breadth-first walk from every node not yet seen. Each walk collects exactly
one component, so the whole decomposition is one pass over the graph and the
code says so. This is the oracle every other backend is compared against, and a
teaching artifact first. See ADR 0002.

The `mode` parameter is the whole subtlety:

  weak    -- follow edges in both directions, ignoring their arrows
  strong  -- a and b are together only if a reaches b *and* b reaches a

On an undirected graph the two coincide, because every edge already goes both
ways. On a directed one they are different questions with different answers,
and no convention decides which "connected components" means.
"""

from __future__ import annotations


def run(converted, params):
    """A partition: which nodes belong together."""
    mode = params.get("mode") or "weak"
    node_ids = converted.node_ids
    directed = converted.directed

    if directed and mode == "strong":
        components = _strong(node_ids, converted.native["edges"])
    else:
        components = _weak(node_ids, converted.native["edges"])

    effective = {
        "mode": mode if directed else "weak",
        "mode_applies": directed,
        "source": "gigi reference implementation",
        "components": len(components),
    }
    return components, effective


def _weak(node_ids, edges):
    """Breadth-first from each unvisited node, ignoring edge direction."""
    neighbours = {node: set() for node in node_ids}
    for source, target, _ in edges:
        neighbours[source].add(target)
        neighbours[target].add(source)

    seen: set[str] = set()
    components = []
    for start in node_ids:
        if start in seen:
            continue
        component = {start}
        frontier = [start]
        while frontier:
            node = frontier.pop()
            for neighbour in neighbours[node]:
                if neighbour not in component:
                    component.add(neighbour)
                    frontier.append(neighbour)
        seen |= component
        components.append(component)
    return components


def _strong(node_ids, edges):
    """Kosaraju's algorithm: two passes, the second on the reversed graph.

    Chosen over Tarjan's because it is two ordinary depth-first walks and one
    reversal, which can be read in a sitting. Tarjan's is one pass and faster,
    and is the right choice in a library rather than in an explanation.
    """
    forward = {node: set() for node in node_ids}
    backward = {node: set() for node in node_ids}
    for source, target, _ in edges:
        forward[source].add(target)
        backward[target].add(source)

    # Pass one: order nodes by when their exploration finished.
    order: list[str] = []
    seen: set[str] = set()
    for start in node_ids:
        if start not in seen:
            _finish_order(start, forward, seen, order)

    # Pass two: walk the reversed graph in reverse finishing order. Each walk
    # collects exactly one strongly connected component.
    assigned: set[str] = set()
    components = []
    for node in reversed(order):
        if node in assigned:
            continue
        component: set[str] = set()
        frontier = [node]
        while frontier:
            current = frontier.pop()
            if current in assigned:
                continue
            assigned.add(current)
            component.add(current)
            frontier.extend(n for n in backward[current] if n not in assigned)
        components.append(component)
    return components


def _finish_order(start, forward, seen, order):
    """Iterative depth-first walk, appending each node once its descendants are
    done. Iterative rather than recursive so a deep graph cannot blow the
    stack -- the one place this file trades a little readability for not
    crashing."""
    stack = [(start, iter(sorted(forward[start])))]
    seen.add(start)
    while stack:
        node, children = stack[-1]
        advanced = False
        for child in children:
            if child not in seen:
                seen.add(child)
                stack.append((child, iter(sorted(forward[child]))))
                advanced = True
                break
        if not advanced:
            order.append(stack.pop()[0])
