# Degree Centrality

*(This template is a worked example. Replace it with your algorithm, keeping
the shape: definition, then the places the definition is under-determined.)*

## Definition

For a graph with `n` nodes, the degree centrality of a node `v` is its degree
divided by the largest degree it could have:

```
C(v) = deg(v) / (n - 1)
```

`deg(v)` is the number of edges incident to `v`. Dividing by `n - 1` makes the
score comparable across graphs of different sizes; without it, the measure is
just a count.

## Where the definition is under-determined

This is the interesting part of any `maths.md`. List the places the maths leaves
a choice open, because those are where engines diverge — and naming them here
tells the next contributor what to test.

- **Direction.** On a directed graph, "degree" can mean in-degree, out-degree
  or their sum. All three are defensible; this implementation uses the sum, and
  so does `nx.degree_centrality`. An engine that returns in-degree only would
  be a `semantic` divergence, not a bug.
- **Self loops.** A self loop adds one to in-degree and one to out-degree, so
  it counts twice under the sum. Some implementations exclude it entirely.
- **Parallel edges.** Whether two edges between the same pair count once or
  twice depends on whether the engine models a multigraph. Gigi preserves
  multiplicity ([ADR 0003](../../docs/adr/0003-graph-data-contract.md)).
- **Normalisation.** Some engines always normalise and give you no way to turn
  it off, which is why the NetworkX implementation in this template has to
  rescale and say so in its effective parameters.
- **n = 1.** The denominator is zero. This implementation returns the raw
  degree rather than dividing.

## Complexity

One pass over the edges: `O(V + E)` time, `O(V)` space.

## Sources

Primary source first, and papers rather than blog posts where a paper exists.

- Freeman, L. C. (1978). "Centrality in social networks conceptual
  clarification." *Social Networks* 1(3), 215–239.
  [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7)
