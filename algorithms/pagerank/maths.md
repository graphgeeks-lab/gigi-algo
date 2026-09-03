# PageRank

## Definition

For a directed graph with `N` nodes and damping factor `d`, PageRank is the
stationary distribution of a random surfer who, at each step, either follows an
outgoing edge (probability `d`) or teleports to a uniformly random node
(probability `1 - d`):

```
r(v) = (1 - d)/N  +  d * sum_{u -> v}  r(u) / outdeg(u)
```

In the weighted case, `outdeg(u)` becomes u's total outgoing weight `W(u)` and
each term is scaled by the edge's weight:

```
r(v) = (1 - d)/N  +  d * sum_{u -> v}  r(u) * w(u,v) / W(u)
```

The scores form a probability distribution: `sum_v r(v) = 1`, and every score is
non-negative.

## Dangling nodes

The formula above is incomplete. A node with no outgoing edges has no `outdeg`
to divide by, and rank that flows into it never flows out — after enough
iterations, all the mass drains into the sinks and the scores stop summing to
one.

The standard repair is to treat a dangling node as if it linked to every node,
which is equivalent to collecting the rank held by dangling nodes and
redistributing it uniformly:

```
dangling_mass = sum over u with outdeg(u) = 0 of r(u)

r(v) = (1 - d)/N  +  d * ( dangling_mass/N + sum_{u -> v} r(u) * w(u,v) / W(u) )
```

**This is a convention, not a theorem.** Uniform redistribution is the choice
Page and Brin made; redistributing proportionally to the teleport vector, or
ignoring dangling mass and renormalising afterwards, are also defensible and
give different answers. `datasets/dangling-small` exists to check whether the
engines have all made the same choice.

## Undirected graphs

PageRank is defined on undirected graphs by treating each edge as two arcs. It
is then closely related to degree centrality: on a connected undirected graph
the stationary distribution is proportional to degree, and damping only pulls
it towards uniform. Not every engine implements this case — see
`rustworkx-directed-only` in `algorithm.yaml`.

## Convergence

Power iteration converges geometrically with ratio `d`: after `k` iterations the
error is on the order of `d^k`. At `d = 0.85`, 100 iterations gives roughly
`10^-8`, which is why engines that cap at 100 iterations essentially never hit
the cap at the usual damping factor — and why they can at `d = 0.99`.

igraph's default solver, PRPACK, does not iterate at all: it solves the linear
system directly. This is why igraph agrees with the reference implementation to
around `1e-13` while power-iteration engines stop at their tolerance, typically
`1e-6`.

## Complexity

Each iteration touches every edge once: `O(V + E)` time and `O(V)` space, for
`k` iterations `O(k(V+E))`.

## Sources

- Page, Brin, Motwani, Winograd, *The PageRank Citation Ranking: Bringing Order
  to the Web* (1998).
- Langville & Meyer, *Google's PageRank and Beyond* (2006) — chapters 4 and 6
  cover dangling nodes and the sensitivity of the ranking to `d`.
