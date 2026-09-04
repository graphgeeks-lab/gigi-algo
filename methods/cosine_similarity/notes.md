# Cosine Similarity — backend notes

Everything below was measured by `gigi verify cosine_similarity`, not read from
documentation.

Backends: reference, SciPy 1.18.1, scikit-learn 1.9.0. Fixtures:
`vectors-small`, `vectors-with-zero`, `vectors-single`.

## Where they agree

On `vectors-small` — four vectors, one parallel pair, one antiparallel pair,
orthogonality elsewhere — all three backends return the same six numbers to
within 1e-12, which is the tolerance this entry is verified at. That is a
tighter bar than the graph methods use, and it is fair: there is nothing
iterative here, so two correct implementations of a dot product over four
numbers should agree to very nearly the last bit. They do.

On `vectors-single` all three return an empty result. One vector is no pairs,
and a backend that invented a self-pair would be caught by the empty
comparison rather than by a special case in the harness.

## Where they disagree: the zero vector

One fixture, `vectors-with-zero`, holds three vectors of which one is all
zeros. Two of the three pairs involve it, and the cosine of those pairs is
`0/0` — undefined by the definition, so each library has invented an answer.

| pair | reference | SciPy | scikit-learn |
|---|---|---|---|
| `p\|q` | *declined* | `NaN` | `0.0` |
| `p\|r` | 0.0 | 0.0 | 0.0 |
| `q\|r` | *declined* | `NaN` | `0.0` |

Three backends, three answers, on the smallest fixture that can produce the
question. Neither library is wrong — the definition does not decide — but they
cannot both be silently correct in the same pipeline.

**SciPy** (`scipy-cosine-zero-vector-nan`, severity high) divides by a zero
norm and returns NaN. This is the same failure mode as the rustworkx singleton
in `degree_centrality`, in a different library and a different domain, which is
the argument for checking finiteness on every run rather than per method — and
`scores_finite` did catch it here without anyone thinking to look.

**scikit-learn** (`sklearn-cosine-zero-vector-is-zero`, severity medium) is the
quieter one and the worse one. Its normaliser leaves an all-zero row as all
zeros, so the dot product is zero and the pair is reported as orthogonal. A
zero vector — an empty document, a record with no features, a failed embedding
— comes back as *known to be dissimilar to everything*, when the truth is that
nothing is known about it. Anything ranking by similarity places it last rather
than excluding it, and no error is raised at any point.

We rate the NaN as higher severity than the 0.0 only because it is more likely
to be noticed in the same session it was introduced. By the standard of *how
wrong is the answer someone acts on*, the 0.0 is worse.

## What pinning the parameter does

With `zero_vector_policy` unset, the three backends disagree, and that is what
the two divergence entries record and what CI re-runs on every commit. With it
pinned to `undefined` — which is what verification does — every backend declines
the undefined pairs, all three agree exactly, and the comparison is about the
measure rather than about three different opinions on `0/0`.

That is the whole shape of the argument this repository makes, and this is the
first place it has been made outside graphs.

## Adapter notes

- **SciPy** returns the condensed upper triangle from `pdist`, in the same pair
  order Gigi builds its result keys — (0,1), (0,2), …, (1,2), … — so mapping
  back to ids is a zip rather than a lookup. If that order ever changed, the
  known-answer case `vectors_small_all_pairs` would fail loudly rather than
  quietly mislabelling every score.
- **scikit-learn** returns the full `n × n` matrix including the diagonal of
  ones. The adapter takes the strict upper triangle. Recorded as the
  `self_pairs` and `pair_ordering` choice points because it is a decision, not
  a fact about the measure.
- The scikit-learn adapter finds zero vectors from the **input**, not from the
  output: a `0.0` in its result is indistinguishable from a genuinely
  orthogonal pair, which is precisely the problem with that convention.

## Not tested here

- Sparse vectors. The measure is defined identically on them; the
  representation question belongs with the data-structures work.
- Vectors with non-finite values. The loader rejects them, so no backend ever
  sees one. If that changes, this is where the disagreement will show up first.
- High dimensions, where the concentration of cosine similarity around zero
  becomes a real problem for nearest-neighbour work. That is a property of the
  measure worth documenting, but it is not a backend disagreement and nothing
  here would catch it.
