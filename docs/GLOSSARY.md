# Glossary

The words this project leans on, in plain language, with where each one lives.
Read in order — each builds on the one before.

---

### Engine

A library that actually runs graph algorithms: NetworkX, igraph, rustworkx.
Gigi never reimplements them; it calls them and records what they did. One
adapter per engine, in `gigi/adapters/`.

### Reference implementation

The version of an algorithm written to be *read* — plain Python, no library
calls, one line of code per line of maths. It lives at
`algorithms/<id>/implementations/reference.py` and plays two roles: a teaching
artifact, and the **oracle** every engine is compared against.

Because everything is checked against it, it is the one thing nothing else
checks. That is what known answers (below) are for.

### Divergence

Two engines, the same algorithm, the same graph, **different answers**. The
thing this project exists to find.

Usually caused by a default nobody typed: NetworkX runs *weighted* PageRank if
the graph happens to have an attribute called `weight`; igraph ignores it. Same
call, different question answered, no warning.

A divergence is recorded in `algorithm.yaml` under `divergences:` with a
`detect:` block that names the fixture, the two engines and the expected
outcome — so CI re-runs it. **A divergence that stops reproducing fails the
build**, because stale documentation is worse than none.

Categories say what *kind* of difference it is: `default` (an engine default
differs), `semantic` (the engines mean different things), `numeric`
(tolerance-level noise), `unsupported` (one engine refuses), `bug` (one engine
is wrong, as far as we can tell).

### Invariant

Something that must be **true of the output**, whatever the engine. PageRank
scores sum to one; degree centrality is never negative; nothing is NaN.

Declared in `maths.invariants` as two lines of YAML, and then **executed on
every run, on every engine, on every fixture**. An invariant whose `id` names
no check in `gigi/invariants.py` fails the build — a property that is written
down but never checked is a comment.

Invariants catch a different class of problem from divergences. A divergence
says two engines disagree; an invariant says an engine is wrong on its own
terms. The `scores_finite` invariant is how rustworkx's NaN on a one-node graph
was caught.

### Choice point (`under_determined`)

A place where **the definition leaves a decision open**. Where does the rank of
a node with no outgoing edges go? Does a self loop count once or twice? What is
the degree centrality of the only node in a one-node graph?

The definition does not say, so every implementation has to pick — and where
implementations pick differently, you get a divergence. Choice points are
recorded in `maths.under_determined` *before* anything is run: they are the
test plan. A divergence records where engines *did* differ; a choice point
records where they *could*.

Each one names the fixture that settles which answer the engines chose, and
any divergence it turned out to cause. A choice point with neither is one
nothing has tested yet, and `gigi review` says so.

### Fixture

A small graph, in `datasets/`, chosen because it puts pressure on one specific
decision. `dangling-small` has sink nodes; `self-loop-small` has self loops;
`empty` and `single-node` are the degenerate cases every implementation has to
survive and few are tested on. Stored as CSV so a change is reviewable in a
diff.

### Known answer

An expected result that **did not come from running the code**. Every node in
a directed 4-cycle scores 0.25 under PageRank — by symmetry, before any
software exists. Cases live in `algorithms/<id>/tests/expected.yaml`, and each
one must say in `derived` where its number came from: symmetry, a closed form,
a hand count, a worked example in a paper.

This is the reference implementation's only independent check. A case derived
by running the code checks the code against itself; a case derived from the
definition checks that the code implements the definition.

### Requested vs effective parameters

What the caller asked for, and what the engine actually used — recorded
separately on every run. The gap between them is where defaults hide. Asking
NetworkX for PageRank with no `weight` argument is *requesting* nothing about
weights; the *effective* value is `weight="weight"`, and that is the whole
story of the first divergence this project found.

### Verification

`gigi verify <algorithm>` asks two separate questions and never mixes them:

1. With every ambiguous parameter pinned, **do the engines agree** with the
   reference? Any difference not covered by a declared divergence fails.
2. Does every **declared divergence still reproduce** under the conditions the
   registry says it does? Any that stopped fails.

Invariants are asserted throughout. An invariant failure on a fixture named by a
declared divergence is explained, not a failure — the same rule as for score
differences.

### Maturity

How much an entry has earned. `frontier` (it exists), `emerging` (the maths is
stated and independently checked), `stable` (every claim is testable and has
been tested), `historical` (frozen, kept for the record).

Each tier has a stated price in `gigi/requirements.py` — the *only* place it is
defined. `gigi review` shows what an entry meets and exactly what the next tier
would take; the test suite refuses an entry claiming a tier it has not earned,
and `gigi promote` refuses to move one that has not.

`frontier` is the tier with teeth: those entries **will not run** without an
explicit `--allow-frontier` or `GIGI_ALLOW_FRONTIER=1`, enforced in the harness
so every caller inherits it. See [MATURITY.md](MATURITY.md).

### Family

A **question**, not a label. `centrality` is "Which nodes matter, and in what
sense of matter?"; `traversal` is "In what order do I reach the nodes?". An
algorithm belongs to a family when it answers that question, which is what
makes the taxonomy useful for *choosing* rather than merely filing. Defined in
`families/families.yaml`; a `family:` that does not resolve is an error.

### Relationship

A typed edge between algorithms, with a condition where one applies. "PageRank
*generalizes* eigenvector centrality, and coincides with it as damping
approaches 1 on a strongly connected graph" tells a reader — or an agent —
when a substitution is legitimate. `see also` would not. Relationships are
mirrored on both ends and CI checks that they are.

### Provenance vs credits

Two attribution questions that are routinely collapsed into one and must not
be:

- **`provenance:`** — who created the algorithm. Original authors, the original
  work, precursors, and `attribution_notes` for the messy parts. Never a single
  `inventor:` field, because the history is rarely that clean.
- **`gigi:`** — who did the work *here*: wrote the spec, the reference, an
  adapter; curated a fixture; found a divergence (`discovered_by`). Every id
  resolves against `people/people.yaml` or the build fails.

Profiles show lineage, never a score.

### Review

`gigi review <algorithm>` splits the work of judging a contribution into what a
machine settled (the requirements of the claimed maturity, plus what happened
when it ran), what is merely absent (the next contribution), and what only a
person can decide — a deliberately short list, led by the one question that
matters most: does the reference implementation compute what the definition
says?

---

If a word you meet in the code or the specs is not here, that is a gap in this
file. Add it.
