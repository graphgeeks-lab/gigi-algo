# Connected Components

## Definition

Define a relation on the nodes: `u ~ v` when a path joins `u` and `v`.

This is an **equivalence relation**:

- *reflexive* — `u ~ u` by the empty path, which is why an isolated node is a component of one rather than a member of nothing;
- *symmetric* — if a path goes from `u` to `v`, the same path read backwards goes from `v` to `u` (undirected), or the definition demands both directions explicitly (strong);
- *transitive* — paths concatenate.

The **connected components** are its equivalence classes, written `V/~`.

That framing is not decoration. A quotient set has *elements, not names*: there is no fact of the matter about which component is "the first one". Every label a library attaches is its own invention, which is why Gigi's comparator compares groupings and ignores labels, and why the known-answer cases give expected answers as unordered lists of unordered lists.

## Which paths count

On a directed graph, "a path joins them" splits into two different questions:

```
weak     ignore the arrows;  u ~ v  if any undirected path joins them
strong   respect them;       u ~ v  only if u ⇝ v and v ⇝ u
```

On an undirected graph they coincide, because every edge already goes both ways.

They are genuinely different answers, not a technicality. On `a → b → c`:

| mode | components |
|---|---|
| weak | `{a, b, c}` |
| strong | `{a}`, `{b}`, `{c}` |

One component or three, from the same three nodes and the same two edges. No convention settles which one bare "connected components" means, so Gigi makes it the `mode` parameter and defaults to `weak`.

## Two structural facts

**The strong decomposition refines the weak one.** Every strong component sits inside exactly one weak component, so:

```
|C_strong(G)| ≥ |C_weak(G)|
```

A backend reporting fewer strong components than weak ones has a bug, and no fixture is needed to know it.

**The condensation is a DAG.** Contract each strong component to a single node and keep the edges between them; the result has no cycles. If it had one, the two components on that cycle would reach each other both ways — and would therefore be one component, not two. This is not a curiosity: it is what `components_are_maximal` checks when `mode` is `strong`.

## Where the definition is under-determined

Less than you would expect, and that is the finding. The equivalence-relation definition settles almost everything: isolated nodes are components of one (by reflexivity), self loops change nothing (reflexivity again), parallel edges change nothing (they repeat an existing path). All four backends agree on all of it.

What is left open is **which question** is being asked, and the libraries disagree about how to handle *that*:

| | on a directed graph, plain `connected_components` | on an undirected graph, asked for `strong` |
|---|---|---|
| NetworkX | raises `NetworkXNotImplemented` | n/a — one function for the case |
| igraph | answers, defaulting to weak | answers, returning the weak result |
| rustworkx | separate functions; no ambiguous entry point | raises `TypeError` about `PyGraph` |

igraph is *mathematically* right to answer `strong` on an undirected graph — the two relations are identical there. NetworkX and rustworkx are being strict about a distinction that does not exist in that case. It is a disagreement about strictness rather than about components, which is why it is recorded as a choice point and not a divergence.

## Why the invariants are unusually strong here

Most invariants in this registry are necessary conditions — scores sum to one, nothing is NaN — that a wrong answer could still satisfy. These two are different. Together they are a *characterisation*:

- **connected** — every component is internally reachable. Satisfied on its own by chopping the graph into single nodes.
- **maximal** — nothing could be merged. Satisfied on its own by putting everything in one component.

Neither alone says much. Together, exactly one partition satisfies both, and it is the right one. So a backend that passes both has not been checked against a plausible-looking property — it has been checked against the definition.

This is also why the checks needed to see the input. "Every component is connected" is a claim about a partition *and the graph it partitions*, and "maximal" additionally depends on which question was asked. An invariant that could only look at the result could assert nothing here beyond "the labels are strings".

## Complexity

`O(V + E)` time and `O(V)` space, for both modes.

- **weak** — breadth-first search restarted at every unvisited node. Each node and edge is touched once across all the restarts, which is why repeated traversal does not make it quadratic.
- **strong** — Tarjan's algorithm does it in one depth-first pass. The reference implementation here uses Kosaraju–Sharir instead: two ordinary walks and one edge reversal, same complexity, larger constant, and readable in a sitting. That trade is [ADR 0002](../../docs/adr/0002-reference-optimises-readability.md) applied — the reference is a teaching artifact first and an oracle second.

## Reading

- Tarjan, *Depth-First Search and Linear Graph Algorithms*, SIAM J. Comput. 1(2), 1972. [doi:10.1137/0201010](https://doi.org/10.1137/0201010) — strong components in one pass.
- Sharir, *A strong-connectivity algorithm and its applications in data flow analysis*, 1981 — the two-pass method, usually credited to Kosaraju, who never published it. Worth knowing before citing him.
- Whitney, *Congruent graphs and the connectivity of graphs*, 1932 — connectivity as a structural property in its own right.
