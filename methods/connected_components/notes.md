# Connected Components — backend notes

Everything below was measured by `gigi verify connected_components`, not read
from documentation.

Backends: reference, NetworkX 3.6.1, python-igraph 1.0.0, rustworkx 0.18.1.
Eleven fixtures, forty-four runs.

## They all agree

**Zero divergences.** This is the first method in the registry where four
backends produce the same answer on every fixture, including the ones built to
break things: the empty graph, the single node, the isolated node, the self
loop, the duplicate edge.

That is worth stating plainly, because a registry that only ever records
disagreement would be a bug tracker with extra steps. Agreement measured across
four independent implementations on adversarial fixtures is evidence too — and
it is evidence we did not have until it was run. PageRank and degree centrality
both looked this safe beforehand and were not.

The explanation is in the maths rather than in the libraries being careful. The
equivalence-relation definition settles nearly everything a multigraph can throw
at it:

| fixture | what could have gone wrong | what happened |
|---|---|---|
| `empty` | a division, an index, an empty-sequence error | all four return an empty partition |
| `single-node` | the 0/1/NaN split that degree centrality hit here | all four return one component of one |
| `disconnected-small` | isolated `n6` dropped by an edge-driven implementation | all four give it its own component |
| `self-loop-small` | a self loop counted as connectivity | changes nothing, in all four |
| `duplicate-edge-small` | parallel edges double-counted, as rustworkx does for degree | changes nothing, in all four |

Reflexivity gives the isolated node and the self loop for free; a parallel edge
repeats a path that already exists. There is nothing left for an implementation
to be creative about, and none of them were.

## Where they do disagree: which question they will answer

The disagreement is one level up, about whether the question is well posed at
all.

| call | NetworkX | igraph | rustworkx |
|---|---|---|---|
| `connected_components` on a **directed** graph | `NetworkXNotImplemented` | answers, defaulting to weak | no ambiguous entry point |
| strong components on an **undirected** graph | n/a | answers, returning the weak result | `TypeError: 'PyGraph' object is not an instance of 'PyDiGraph'` |

igraph is mathematically right in the second row — on an undirected graph weak
and strong are the same relation, so there is a correct answer and it returns
it. NetworkX and rustworkx refuse a question that has an answer.

**None of this reaches a Gigi user**, because the adapters route by mode and
direction before calling anything. That is a deliberate choice and it is worth
being explicit about: the adapter is hiding a real difference in library
strictness. It is recorded as the `undirected_strong` choice point, and each
adapter reports the function it actually called in its effective parameters, so
the routing is visible in every run rather than buried in an adapter.

It is recorded as a choice point rather than a divergence because the backends
do not disagree about *components* — they disagree about how strict to be with
the caller. A divergence in this registry means different answers to the same
question, not different opinions about whether to take the question.

## The labels are noise, and that is the interesting part

All four backends return the same grouping and none of them return the same
labels:

| backend | shape returned | on `a→b`, `c` |
|---|---|---|
| reference | list of sets of ids | `[{a,b}, {c}]` |
| NetworkX | iterator of sets of ids | `[{a,b}, {c}]` |
| igraph | membership vector, one label per vertex | `[0, 0, 1]` |
| rustworkx | list of sets of node *indices* | `[{0,1}, {2}]` |

And on a strong decomposition igraph counts components in reverse topological
order while rustworkx counts in reverse index order, so the same partition comes
back with labels permuted differently by each.

Comparing labels would have reported four correct implementations as four
different answers. Gigi's normaliser rewrites labels to `c0, c1, …` ordered by
each component's earliest member, and the comparator compares groupings rather
than labels — so the arbitrary part is discarded before anything is judged. This
is the whole reason `partition` could not reuse the score comparator.

## Not tested here

- **Large graphs.** Every fixture is under ten nodes. The reference
  implementation is `O(V+E)` but its constants are terrible, and nothing here
  would notice if a backend were accidentally quadratic.
- **Recursion depth.** The reference's depth-first pass is iterative
  specifically so a deep graph cannot blow the stack, but no fixture is deep
  enough to prove it. A path of ten thousand nodes would.
- **Longer condensations.** `two-clusters-directed` was added while writing
  these notes, because `dangling-small` under `mode: strong` gives six
  singletons and exercised the acyclic branch of `components_are_maximal` only
  vacuously. It is two mutually reachable pairs joined by one one-way edge: one
  weak component, two strong ones, and a condensation that is a real DAG. That
  branch is now checked, but on four nodes; a condensation with a longer chain
  is still untested.
