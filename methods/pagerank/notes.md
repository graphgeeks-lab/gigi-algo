# PageRank — backend notes

What follows was measured by `gigi verify pagerank`, not read from
documentation. Every claim here has a corresponding entry in `method.yaml`
and a check in the conformance suite.

## The weight default is the dangerous one

`nx.pagerank(G)` defaults to `weight="weight"`. If the graph carries an edge
attribute of that name — and a graph loaded from a table with a `weight` column
will — NetworkX runs **weighted** PageRank. `igraph.Graph.pagerank()` defaults
to `weights=None` and runs **unweighted** PageRank on the same graph, ignoring
the attribute entirely. `rustworkx.pagerank()` takes a `weight_fn` callable and
defaults to unweighted.

Measured on `weighted-small` with no parameters given:

| backend | a | b | c |
|---|---|---|---|
| reference (unweighted) | 0.233918 | 0.333333 | 0.432749 |
| networkx | **0.118150** | 0.400793 | 0.481057 |
| igraph | 0.233918 | 0.333333 | 0.432749 |
| rustworkx | 0.233919 | 0.333333 | 0.432748 |

That is a 49% relative difference on node `a` between two backends running "the
same algorithm with default settings". Nothing warns you.

The practical consequence: porting an analysis from NetworkX to igraph silently
changes the question being answered, and porting it back changes it again. If
weights matter, say so; if they do not, say that too. Gigi's `weight_property`
parameter is deliberately tri-state (`null` = backend default, `false` =
explicitly unweighted, a string = use that column) so that the ambiguity is
visible in the call rather than hidden in the backend.

## rustworkx is directed-only

`rustworkx.pagerank` accepts `PyDiGraph` and raises `TypeError` on `PyGraph`.
NetworkX, igraph and the reference implementation all handle undirected graphs
by treating each edge as two arcs, and agree with each other when they do.

This is worth stating precisely because it is a support question that depends on
the *graph*, not just the algorithm: "does rustworkx support PageRank" is yes,
and "can rustworkx run PageRank on this graph" is no.

## Where the backends agree

Verified, not assumed — these were checked and no difference above tolerance was
found:

- **Dangling nodes** (`dangling-small`): all four backends redistribute the
  dangling mass uniformly. Agreement to `1e-13` against the reference for
  igraph, `1e-6` for the power-iteration backends.
- **Self loops** (`self-loop-small`): all four keep them. None silently drops a
  self loop, and none double-counts one.
- **Isolated nodes** (`disconnected-small`): all four score the isolated node
  `n6` at 0.029126 — the teleport share `(1-d)/N = 0.025` plus its portion of
  the redistributed dangling mass — and none drops it from the result.
- **Parallel edges** (`duplicate-edge-small`): all four count multiplicity
  rather than collapsing duplicates, agreeing to `1e-12`. Worth checking,
  because collapsing would have halved `b`'s inflow.

## Numerical agreement, and its limits

igraph's PRPACK solves the system directly, so it agrees with the reference to
roughly `1e-13`. NetworkX and rustworkx iterate to a default tolerance of
`1e-6` and land within about `1e-6`. That is fine for ranking, and not fine for
equality: two backends can order tied-ish nodes differently at the sixth decimal
place. `comparison.absolute_tolerance` in `method.yaml` is set to `1e-6` for
exactly this reason, and verification pins `tolerance: 1e-12` so that the
backends are compared at convergence rather than at their own stopping points.

## Not yet investigated

- Behaviour at `d` close to 1, where the 100-iteration default cap can bite.
- `personalization` / `nstart` / `dangling` vectors, which NetworkX exposes and
  igraph does not.
- Graphs large enough for NetworkX's `err < N * tol` convergence test to stop
  noticeably earlier than a plain L1 test would.
