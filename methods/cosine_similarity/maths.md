# Cosine Similarity

## Definition

For two vectors `x` and `y` in the same space, the cosine similarity is the dot
product divided by the product of the lengths:

```
cos(x, y) = <x, y> / (||x|| ||y||)
```

where `<x, y> = Σᵢ xᵢyᵢ` and `||x|| = √<x, x>`.

The name is literal. Write the dot product in its geometric form,
`<x, y> = ||x|| ||y|| cos θ`, and the definition rearranges to `cos θ`: the
cosine of the angle between the two vectors, and nothing else. Everything about
how *long* either vector is has been divided out.

An equivalent form, and the one every library actually computes:

```
cos(x, y) = <x/||x||, y/||y||>
```

Normalise, then take the dot product. Algebraically identical; numerically
different, and the difference is where the zero vector becomes a division by
zero rather than a 0/0.

## Why the bound holds

The Cauchy–Schwarz inequality says `|<x, y>| ≤ ||x|| ||y||` for any two vectors,
with equality exactly when one is a scalar multiple of the other. Divide both
sides by `||x|| ||y||` and the statement becomes:

```
-1 ≤ cos(x, y) ≤ 1
```

So the invariant this entry asserts on every run is not a convention or a
clamp — it is a theorem from 1888. A score outside the interval means the
normalisation is broken, not that the data was unusual. That is worth stating
because the alternative, clipping the result into range, is common and hides
exactly the bug the bound would have found.

Equality at `+1` means the vectors are positive multiples of each other; at
`-1`, negative multiples. Both are reachable, which is why the fixture includes
a parallel pair and an antiparallel one.

## Scale invariance

For any `α, β > 0`:

```
cos(αx, βy) = cos(x, y)
```

The scalars come out of the dot product and out of both norms, and cancel. This
one equation is the whole reason to choose this measure and the whole reason to
regret it:

- **Choose it** when magnitude is an artefact — document length, embedding
  norm, how many events happened to be recorded — and only direction carries
  meaning.
- **Regret it** when magnitude *was* the signal. Two customers with identical
  purchasing proportions score 1 whether one spent £10 and the other £10,000.

Cosine does not measure similarity. It measures similarity *after* discarding
scale, and the discarding is not recoverable downstream.

## Where the definition is under-determined

### The zero vector

The interesting one. If `||x|| = 0` the expression is `0/0`, and no amount of
algebra decides it: the zero vector has no direction, so there is no angle to
take the cosine of. Four answers are in circulation, and this repository has
measured three of them:

| answer | who returns it |
|---|---|
| decline the pair; the value does not exist | Gigi's reference implementation |
| `NaN`, propagating the division | SciPy (`pdist`, metric `cosine`) |
| `0.0`, as if orthogonal to everything | scikit-learn (`cosine_similarity`) |
| `1.0` when both are zero, as "identical" | some hand-rolled implementations |

`0.0` is the dangerous one. NaN is loud and something downstream will trip over
it; `0.0` is a plausible number that means *known to be dissimilar* when the
truth is *nothing is known*. An empty document, a record with no features, a
failed embedding — each becomes a confident negative.

Gigi makes it the `zero_vector_policy` parameter. Unset means "whatever the
backend does", which is how the divergence is observed; verification pins it to
`undefined` so the backends can be compared on everything else.

### Self-pairs and orientation

`cos(x, x) = 1` for every non-zero `x`, and `cos(x, y) = cos(y, x)` because the
dot product commutes. So a full `n × n` matrix carries `n(n-1)/2` distinct
numbers and `n(n+1)/2` redundant ones. Gigi's output is one score per unordered
pair, keyed `a|b` with the ids sorted, and asserts that as an invariant.
scikit-learn returns the full matrix; the adapter takes the strict upper
triangle. That is a decision the registry records rather than a fact it hides.

## Cosine distance is not a metric

The distance form, `d(x, y) = 1 - cos(x, y)`, is what SciPy returns and what
much of the surrounding literature means by "cosine distance". It is not a
metric: it violates the triangle inequality. Anything that assumes a metric
space — some clustering algorithms, some spatial indexes, most proofs about
approximation quality — is assuming something this does not provide.

The angular distance `arccos(cos(x, y)) / π` *is* a metric, and is the right
thing to reach for when the triangle inequality is load-bearing.

## Complexity

`O(d)` per pair, `O(n² d)` for all pairs of `n` vectors in `d` dimensions, and
`O(n²)` space for the result. The reference implementation does exactly that
with no attempt to hide it. Both library backends normalise once per vector
rather than once per pair, which is a constant-factor improvement and not a
different algorithm — the answers must agree to within floating-point noise,
and the tolerance here (1e-12) is tight enough that they have to earn it.

## Reading

- Salton, Wong and Yang, *A Vector Space Model for Automatic Indexing*, CACM
  18(11), 1975. [doi:10.1145/361219.361220](https://doi.org/10.1145/361219.361220)
  — the representation that makes the angle mean something.
- Salton, *The SMART Retrieval System*, 1971 — cosine ranking in use before it
  was stated as a model.
- Jaccard, 1901 — an earlier similarity coefficient over sets. Different
  measure, same job, and a reminder that "how alike are these two things" has
  been formalised many times and never once to suit every question.
