# 0012 — A result is not always a number per key

**Status:** accepted; landed with `connected_components`

## Context

Two output kinds shipped before this one, and both were one number per key:
`node_score` keyed by node, `similarity_score` keyed by a canonical pair. They
share a comparator, and [ADR 0011](0011-a-dataset-declares-its-kind.md) argued
that sharing was principled rather than lazy — the *comparison* really is
identical, and only the meaning of the key differs.

That made the extension rule in [ONTOLOGY.md](../ONTOLOGY.md) — *an output kind
must ship a comparator* — cheap to satisfy twice in a row, and therefore
untested. `similarity_score` paid the rule by pointing at a comparator that
already existed.

`connected_components` cannot. Its result is a grouping, and the four backends
label groups four different ways:

| backend | returns | on `a→b`, `c` |
|---|---|---|
| reference | list of sets of ids | `[{a,b}, {c}]` |
| NetworkX | iterator of sets of ids | `[{a,b}, {c}]` |
| igraph | membership vector per vertex | `[0, 0, 1]` |
| rustworkx | sets of node *indices* | `[{0,1}, {2}]` |

On a strong decomposition igraph counts in reverse topological order and
rustworkx in reverse index order, so the same partition comes back permuted
differently by each. Compared as values, four correct implementations are four
different answers.

## Decision

**`partition` is an output kind with its own model and its own comparator.**
`PartitionResult` holds `assignments`, a key-to-label mapping, and exposes
`groups()` — the partition as the mathematical object it is, a set of disjoint
sets. `compare_partitions` compares *that*, never labels.

**Labels are canonicalised on normalisation and carry no meaning.** The
normaliser rewrites them to `c0, c1, …` ordered by each component's earliest
member. The maths says why this is not a convenience: the components are the
equivalence classes of a reachability relation, and a quotient set has elements,
not names. Any label a library attaches is its own invention.

Canonicalising means label comparison would now agree with grouping comparison.
The comparator still compares groupings, because the property is the grouping —
and a future normaliser bug should fail the comparator, not be hidden by it.

**The result union is discriminated.** `ScoreResult.kind` is constrained to the
two score kinds and `PartitionResult.kind` to `partition`, so a stored run
round-trips back into the right class and a score result cannot claim to be a
partition.

**Tolerances do not apply and are not quietly accepted.** `compare_partitions`
takes them to match the comparator signature and ignores them; the method
declares `0.0` rather than a plausible-looking number, so nothing can read a
tolerance as meaning something here. There is no such thing as approximately the
same grouping.

**An invariant can see the input and the question.** Checks now receive a
`CheckContext` — the dataset, and the *effective* parameters. This is the part
worth arguing about, because it is a change to every existing check for the
benefit of one new method.

The argument is that without it, a partition invariant can assert almost
nothing. "Every component is connected" is a claim about a partition *and the
graph it partitions*. And `components_are_maximal` additionally depends on which
question was asked: under `weak` no edge may cross between components, while
under `strong` crossing edges are the entire point and the claim becomes that
they form no cycle. An invariant that ignored the parameters would have been
false half the time — and an invariant that is false under a supported setting
is not an invariant.

## Consequences

**The invariants here are stronger than anywhere else in the registry.** Most
are necessary conditions a wrong answer could still satisfy. Connected and
maximal together are a *characterisation*: connectivity alone is satisfied by
chopping the graph into single nodes, maximality alone by putting everything in
one component, and exactly one partition satisfies both. A backend passing both
has been checked against the definition, not against a plausible property.

**Zero divergences, and that is a result.** Four backends agreed on every one of
eleven fixtures, including the empty graph, the isolated node, the self loop and
the duplicate edge — the same fixtures that split three backends three ways on
`degree_centrality`. The reason is in the maths: the equivalence-relation
definition settles the multigraph cases by reflexivity, leaving nothing for an
implementation to be creative about.

A registry that only recorded disagreement would be a bug tracker. Measured
agreement across four independent implementations is evidence too, and it is
evidence nobody had before it was run.

**What the adapters hide, on purpose.** NetworkX raises on directed input to
`connected_components`; rustworkx raises `TypeError` for strong components on an
undirected graph; igraph answers both. Gigi's adapters route by mode and
direction, so none of it reaches a caller. That is a real difference being
smoothed over, so it is recorded as the `undirected_strong` and `directed_mode`
choice points, and every adapter reports the function it actually called. A
divergence here means different answers to the same question — not different
opinions about whether to accept the question.

**Known answers had to grow a second shape.** `expected: dict[str, float]`
cannot express a grouping, so `expected_components` holds a list of lists,
unordered at both levels. Adding it exposed that `expected: {}` had been
asserting nothing at all — the comparison loop had nothing to iterate and passed
whatever came back. An empty expectation now asserts emptiness.

**The budget went up again**, from 2,400 to 2,700, and that is the third raise
in three PRs. PLAN.md carries the argument for why it should be the last one.
