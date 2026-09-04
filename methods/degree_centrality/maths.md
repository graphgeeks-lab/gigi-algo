# Degree Centrality

## Definition

For a graph with `n` nodes, the degree centrality of a node `v` is its degree
divided by the largest degree it could have:

```
C(v) = deg(v) / (n - 1)
```

`deg(v)` is the number of edge **incidences** at `v`. A node cannot be adjacent
to more than the other `n - 1` nodes, so dividing by `n - 1` puts scores on a
scale that is comparable across graphs of different sizes. Without that
division the measure is a count, not a centrality.

On a directed graph the definition splits three ways:

```
C_all(v) = (deg⁻(v) + deg⁺(v)) / (n - 1)
C_in(v)  =  deg⁻(v)            / (n - 1)
C_out(v) =  deg⁺(v)            / (n - 1)
```

All three are called "degree centrality" in the literature. Gigi makes the
choice explicit as the `mode` parameter rather than picking one silently.

## Where the definition is under-determined

The interesting part. Degree centrality is trivial to compute and surprisingly
easy to disagree about.

- **Direction.** In, out, or their sum — see above. Every backend here defaults
  to the sum, but that is a convention rather than a consequence, and a paper
  reporting "degree centrality" on a directed graph has usually not said which.
- **Incidences or neighbours?** Two edges between the same pair are two
  incidences but one neighbour. Gigi counts incidences, so parallel edges count
  twice. An implementation that counts distinct neighbours is computing
  something else, and the difference only shows up on multigraphs.
- **Self loops.** On a directed graph a self loop is both an out-edge and an
  in-edge, so it adds 2 under `mode: all`. Counting it once, or not at all
  (on the grounds that a node is not its own neighbour), are both defensible.
- **Normalisation.** Whether to divide by `n - 1` at all, and whether the caller
  can turn it off. The three backends here take three different positions —
  NetworkX and rustworkx always normalise, igraph never does.
- **n = 1.** The denominator is zero. This implementation returns the raw
  degree rather than dividing.
- **Weights.** Summing edge weights instead of counting edges gives *strength*,
  a related but distinct measure. Gigi's degree centrality ignores weights;
  strength belongs in its own entry rather than behind a flag here.

## Range

With `mode: all` on a directed graph a node can score up to 2 — it may have
`n - 1` in-edges and `n - 1` out-edges — and with parallel edges there is no
upper bound at all. Only on a simple undirected graph is `C(v)` confined to
`[0, 1]`. This is why the spec asserts non-negativity and finiteness but *not*
that scores lie in the unit interval: an invariant that does not hold is worse
than no invariant.

## Relationship to other centralities

Degree is the degenerate case of the path-summing centralities. Katz centrality
sums damped contributions over paths of every length; set the attenuation
factor to zero and only paths of length one survive, which is degree. PageRank
adds the further step of dividing each node's contribution among its
out-neighbours.

That makes degree the baseline worth running first. When a more expensive
centrality ranks the top nodes the same way degree does, it has told you
nothing you did not already know cheaply — and when it disagrees, the
disagreement is the finding.

## Complexity

One pass over the edges: `O(V + E)` time, `O(V)` space.

## Sources

- Freeman, L. C. (1978). "Centrality in social networks conceptual
  clarification." *Social Networks* 1(3), 215–239.
  [doi:10.1016/0378-8733(78)90021-7](https://doi.org/10.1016/0378-8733(78)90021-7)
- Bavelas, A. (1950). "Communication patterns in task-oriented groups."
  *Journal of the Acoustical Society of America* 22(6), 725–730.
