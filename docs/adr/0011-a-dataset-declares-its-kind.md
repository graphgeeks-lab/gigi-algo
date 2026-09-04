# 0011 — A dataset declares its kind, and a backend says what it takes

**Status:** accepted; landed in PR 2b with `cosine_similarity`

## Context

[ADR 0010](0010-general-schema-narrow-content.md) generalised the *schema* while
keeping the content graph-only. That left the claim untested: a `MethodSpec`
with a discriminated `inputs` union proves nothing if every method in the
registry consumes a graph and the runtime below it can only load one.

`cosine_similarity` was chosen as the first non-graph entry precisely because
it is small enough to hold in one hand and still breaks four assumptions the
runtime had made:

1. `load_graph(dataset_id)` — one loader, returning one container.
2. A backend converts a `GraphData` and nothing else.
3. A result is keyed by node, and every node owes a score.
4. A "backend" is a graph library.

None of those are wrong for graphs. All of them are wrong in general.

## Decision

**A fixture declares its kind in `dataset.yaml`; it is never inferred.**
`kind: graph` or `kind: vectors`, discriminated exactly the way a method's
`inputs` are — one vocabulary for what a fixture holds, what a method consumes
and what a backend converts. `gigi/data.py` is the single door: `load_dataset`
returns whichever container fits, `profile_dataset` profiles it, and everything
above asks for a fixture by id.

A loader that guesses from the files it finds is one bad filename away from
reading a graph as something else. The cost of declaring the kind is one line
in a file that already exists.

**A backend declares what it can be handed.** `require_graph(NAME, data)` and
`require_vectors(NAME, data)` refuse the wrong kind by name, in the adapter,
rather than failing three frames down with an `AttributeError`. `registry.
BACKEND_INPUT_KINDS` is the same fact in the form the review needs, so that
`gigi review` never tells a contributor to write a NetworkX implementation of a
measure over vectors. The two are checked against each other in
`tests/test_vectors.py`.

The reference backend is the exception: it takes every kind, because being the
oracle for every method is its whole job.

**A result is keyed by whatever the method produces, not by node.**
`ConvertedGraph.result_keys` is the node list; `ConvertedVectors.result_keys` is
every unordered pair, in canonical `a|b` form. `normalize_scores` takes the keys
and the output kind, and the harness never asks what kind of thing it is
running.

**Some keys may legitimately have no answer.** `keys_are_complete` is True for a
graph — a node missing a score is a bug — and False for a pairwise measure,
because a zero vector has no direction and the cosine of any pair involving one
does not exist. A backend declining a key is a *finding for the comparator*
rather than an error during normalisation, and the comparator reports two
backends that decline different keys as disagreeing.

## Consequences

**What it bought, concretely.** The zero-vector fixture produced two divergences
on the first run: SciPy returns `NaN`, scikit-learn returns `0.0`, and the
reference declines the pair. The second is the more dangerous — a failed
embedding reported as *known to be dissimilar* rather than *no answer* — and
neither library is wrong, because the definition does not decide. That is the
same argument the graph entries make, in a domain that shares no code with them.

**The extension rule holds.** Adding `similarity_score` required its comparator
before any method could claim it (`tests/test_schema.py`), and adding `vectors`
as a dataset kind required a loader and a profiler before any fixture could
declare it. Neither was free, and that is the point.

**What did not change.** The harness is still three functions. No method-kind
branch was added to `run`, `compare` or `verify`; the only `isinstance` checks
outside the data layer are the two guards above and one in
`explicit_parameters`, where `weight_property` is derived from a graph and a
method that does not consume a graph never declares it.

**What we deliberately did not do.** Sparse vectors, non-finite values and a
column-meaning vocabulary for non-graph data are all absent. The first two are
rejected by the loader with a clear message; the third prints "no
column-meaning check for this kind of data yet" rather than "nothing to flag",
because a clean bill of health nobody earned is worse than an admission.

**The next kind will be cheaper, and should still be resisted.** The pattern is
now: a metadata model, a loader with validation, a profile, a `Converted*`
saying how results are keyed, and at least one method that needs it. A kind
without a method is a plan, and plans belong in PLAN.md.
