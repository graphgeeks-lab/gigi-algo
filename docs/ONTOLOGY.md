# The ontology, and how it extends

**Status:** design, not yet built. The registry today knows about graph
algorithms only. This is the shape it should grow into, and — more importantly
— the rules for growing it without the schema turning into a shape that fits
everything and helps with nothing.

The product principle, borrowed from the generalisation spec and worth keeping
verbatim:

> **General schema, narrow initial content.**

v0.1 ships graph algorithms and says so publicly. The schema underneath is
general before the content is broad, because the cheapest moment to rename
`AlgorithmSpec` is *before* anyone has installed it.

---

## 1. Two roots, not one

The spec proposes `MethodSpec` replacing `AlgorithmSpec`. Agreed. But there is
a second root it does not have, and it matters as much:

| | **Method** | **Structure** |
|---|---|---|
| answers | "how do I compute this?" | "how do I hold this so computing it is cheap?" |
| examples | PageRank, Dijkstra, cosine similarity, Fellegi-Sunter | CSR, adjacency list, binary heap, inverted index, R-tree, trie |
| declares | inputs, output, parameters | the operations it provides, and at what cost |

A data structure is not a kind of method, so it should not be a `MethodKind`.
Forcing it into one would give every structure an empty `inputs`/`output` and
every method an empty `operations` — the classic sign of a union that should
have been two things.

**But they share almost everything**: provenance (B-trees have authors and a
1970 paper), credits, maturity, `maths` with invariants, `under_determined`,
`divergences`, known answers. When `StructureSpec` is actually built, that
common core gets factored out. Not before — we have a rule against abstractions
with one implementation, and it applies to us.

### Why structures earn their place

Our `complexity` field today is a bare string:

```yaml
complexity:
  time: O(k(V+E))
```

That claim is **silently assuming O(1) adjacency access**. On an edge list,
PageRank is `O(k·V·E)`. Dijkstra is `O((V+E) log V)` *with a binary heap* and
`O(E + V log V)` *with a Fibonacci heap* — the complexity of an algorithm is
not a property of the algorithm alone, and right now we assert it as though it
were.

So the structure layer is not scope creep. It is what makes a claim we are
already making honest.

---

## 2. The join between them: operations

Methods and structures meet at **operations**, and this is the piece that makes
the whole thing computable rather than decorative:

```
Method ──NEEDS_OPERATION──► Operation ◄──PROVIDES──── Structure
                                                (at a stated cost)
```

```yaml
# in a method
needs_operations:
  - id: neighbours_out
    per: iteration
  - id: degree_out

# in a structure
provides_operations:
  - id: neighbours_out
    complexity: O(deg(v))
  - id: degree_out
    complexity: O(1)
```

That single join buys four things:

1. **Honest complexity.** `O(k(V+E))` becomes a claim *given* a structure that
   provides `neighbours_out` in `O(deg)`. State the assumption or lose it.
2. **Arboris's planner input, for free.** The spec's §33 wish-list
   (`requires_outgoing_adjacency`, `requires_incoming_adjacency`, `iterative`,
   `whole_graph`) is exactly `needs_operations` written as loose booleans. One
   list, and a planner can ask "which of my physical layouts provides every
   operation this method needs, most cheaply?"
3. **It generalises out of graphs.** Blocking needs `candidates(key)`; an
   inverted index provides it in `O(|bucket|)`, LSH provides it approximately.
   A spatial range query needs `within(bbox)`; an R-tree gives
   `O(log n + k)`, a flat table gives `O(n)`.
4. **Structures get our existing machinery unchanged.** Invariants are *more*
   natural for structures than for methods: "the heap property holds after
   every insert", "in-order traversal of a BST is sorted", "a B-tree's leaves
   are all at the same depth". Those are exactly the property checks
   `gigi/invariants.py` already runs.

**Do the cheap half now.** `needs_operations` on a method is a list — perhaps
ten lines of schema — and it improves the complexity claim immediately.
`StructureSpec` waits until there is a structure worth describing. The edge is
useful with only one end attached.

---

## 3. The objects

Authored by hand (the canonical records):

| object | file | what it is |
|---|---|---|
| **Method** | `methods/<id>/method.yaml` | how to compute something |
| **Structure** | `structures/<id>/structure.yaml` | how to hold something *(later)* |
| **Problem** | `problems/<id>.yaml` | the question, independent of any method |
| **Domain** | `domains/domains.yaml` | graph, similarity, entity_resolution, geospatial |
| **Family** | `families/families.yaml` | a question within a domain |
| **Operation** | `operations/operations.yaml` | the vocabulary methods and structures meet in |
| **Person** | `people/people.yaml` | who did the work here |
| **Dataset** | `datasets/<id>/` | fixtures |

Derived, never authored (`gigi knowledge build`):

```
Paper · Implementation · Backend · Divergence · UseCase · Verifier · Candidate · Experiment
```

**This distinction is load-bearing.** The generalisation spec's §23 lists a
relationship vocabulary including `introduced_by`, `implemented_by`,
`verified_by` and `used_in` — and then says, correctly, "do not manually
duplicate relationships that can be derived." Those four *are* derivable, from
`provenance.original_work`, `backends`, `verification` and `use_cases`. They
belong in the knowledge-graph edge set, not in the hand-authored vocabulary.
Authoring both is how a registry starts contradicting itself.

---

## 4. Extension points, and the price of each

An ontology is extendable if adding to it is cheap *and* the extension cannot
be inert. Every extension point below has a "you must also ship" rule, in the
same spirit as *an invariant must name a check* and *a divergence must have a
detect block*.

| to add a… | you write | you must also ship | enforced by |
|---|---|---|---|
| **domain** | a row in `domains.yaml` | at least one family in it | test: no orphan domains |
| **family** | a row in `families.yaml` | a `question` ending in `?` | already enforced |
| **problem** | `problems/<id>.yaml` | a question, input kinds, output kinds | test: referenced by ≥1 method |
| **method kind** | an enum value | a method using it, and a reviewer note on why an existing kind did not fit | test: no unused kinds |
| **input kind** | a discriminated model | a loader that produces it, and a profiler | test: kind ↔ loader |
| **output kind** | an enum value | **a comparator in `results.py`** | test: kind ↔ comparator |
| **relationship kind** | an enum value | an inverse (or "symmetric"), and mirroring | already enforced |
| **operation** | a row in `operations.yaml` | a method needing it or a structure providing it | test: no orphan operations |
| **invariant** | YAML | a check in `invariants.py` | already enforced |
| **backend** | an adapter module | `available`/`version`/`convert` | already enforced |

The **output kind** rule is the one that will bite, and should. Adding a value
to the enum without a comparator would produce a method nothing can verify —
which is the failure mode the whole project exists to avoid. So: **an output
kind without a comparator fails the build**, exactly like an invariant without
a check.

It has now been paid twice. `similarity_score` arrived with `cosine_similarity`
and reuses `compare_scores`, which is allowed and was argued rather than
assumed: both kinds are one number per key, judged by numeric tolerance over a
matching key set, and only the meaning of the key differs. `probability`,
`partition` and `path` will each need a real comparator of their own. The
**input kind** rule was paid at the same time: `vectors` shipped with
`gigi/vectors.py` (loader and validation) and `profile_vectors`, and the
fixtures declare `kind:` rather than being sniffed.

### Adding a domain, worked

Geospatial, as a concrete test that this is not graph-shaped thinking:

```yaml
# domains.yaml
- id: geospatial
  name: Geospatial
  related: [graph]          # routing sits in both

# families.yaml
- id: spatial_indexing
  domain: geospatial
  question: Which records lie within this region?
```

New input kind `geometry`; new output kinds `geometry_set`, `distance`; new
structures R-tree, quadtree, H3; new operations `within(bbox)`,
`nearest_k(point)`. And — the reason this domain is a good test — a
**semantic interpretation** that is the exact analogue of the graph weight
problem:

> Your coordinates are EPSG:4326 (degrees). This method computes planar
> distance. One degree of longitude is 111 km at the equator and 0 km at the
> pole. Did you mean to project first?

Same failure, different domain. If the semantic layer catches both with one
mechanism, it is the right mechanism.

---

## 5. The semantic layer

This is the part I think is the most valuable idea in the new spec, and the
part most likely to be the reason someone uses Gigi daily.

### Parameters carry a semantic role

```yaml
# PageRank
- name: weight_property
  semantic_role: strength
  interpretation: {higher_means: stronger}

# Dijkstra
- name: weight_property
  semantic_role: cost
  interpretation: {higher_means: worse}
```

Same column, opposite meaning. A user whose `weight` column holds *distance*
and who runs both has asked two contradictory questions and been told nothing.

### The conflict check needs two halves

```
   what the method expects          what the data means
   semantic_role: strength    vs    column `weight` = distance
   ────────────────────────────────────────────────────────────
                    "did you intend to invert?"
```

Gigi owns the left half. It does **not** own the right half, and should not
invent a vocabulary for it — which brings us to interchange.

---

## 6. Interchange: Apache OSSIE

[OSSIE](https://github.com/apache/ossie) is a semantic-model spec for
analytics data: datasets, fields, relationships, metrics, a datatype
enumeration, and an `ai_context` block carrying `instructions`, `synonyms` and
`examples` for LLM consumption.

It is **the missing right half**. OSSIE says what `weight` *means to the
business*; Gigi says what `weight_property` *means to the method*. They are
complementary, and reaching for our own data-semantics vocabulary when a
standard one exists would be the wrong instinct.

**What I would adopt:**

1. **`ai_context` verbatim** — same field name, same shape
   (`instructions` / `synonyms` / `examples`) — on `Method`, `Problem`,
   `Family`, `Parameter` and `Divergence`. This is the user's "one way to
   implement this in various places": anything that already consumes OSSIE
   `ai_context` can consume Gigi's without special-casing. It also gives
   `synonyms` a home, which our recommendation layer will want.
2. **OSSIE's datatype enumeration** for the data-representation layer
   (`String`, `Integer`, `Decimal`, `Float`, `Boolean`, `Date`, `DateTime`,
   `DateTimeTz`, `Opaque`) instead of inventing one.
3. **OSSIE models as an optional input**, so the conflict check reads declared
   business meaning rather than guessing:
   ```bash
   gigi why pagerank --graph transactions/ --semantic-model model.yaml
   ```

**What I would not do: take a dependency.** Vendor the shapes; do not import
the package. OSSIE is young and its schema will move; coupling our registry's
validation to a moving target would mean their release breaks our build. The
cost of copying two small shapes is near zero, and the alias is easy to keep
honest with a test that our `ai_context` model round-trips an OSSIE document.

**Without an OSSIE model**, fall back to a small curated table of column-name
hints (`distance`, `cost`, `duration`, `price` → cost-like; `amount`,
`strength`, `score`, `count` → strength-like) kept as **data, not code**. Two
rules: it *asks*, it never rewrites; and a wrong guess must be cheap to
silence.

---

## 7. `gigi why` is mostly derived

The headline command is not new knowledge — it is a join over what the registry
already holds, which is why it is worth building early:

| line of output | comes from |
|---|---|
| "PageRank answers: *which nodes receive recursive influence…*" | `ProblemSpec.question` |
| "It does not answer: most connections / bridging / shortest route" | `intent.not_for` → those problems' questions |
| "higher edge weight = stronger transition" | `SemanticInterpretation` |
| "Your graph has an edge column named `weight`; NetworkX will use it by default" | the user's `GraphProfile` + the `networkx-weight-default` divergence |

That last row is the whole point. `gigi why pagerank` is documentation;
**`gigi why pagerank --graph mydata/` is advice**, because it reads the data in
front of you and names the divergence that applies to *it*. The flag should
exist from the first version.

`gigi alternatives` is the same trick over `relationships` where
`kind: alternative_to`, printing each target's family question as the "use when
…" line — which is why families being *questions* rather than labels finally
pays off.

---

## 8. The knowledge graph, and the closing loop

Derived, never authored:

```bash
gigi knowledge build   # → dist/knowledge/{nodes,edges}.parquet + knowledge.json
```

Two properties worth designing for deliberately:

- **It is a Gigi dataset.** Emit it in our own `nodes.csv`/`edges.csv`/`graph.yaml`
  shape and `gigi run pagerank --graph dist/knowledge` works. Gigi analyses its
  own registry with its own algorithms. That is a real dogfood, not a demo —
  and a real graph workload for Arboris.
- **CI builds it and fails on a dangling edge.** A knowledge graph is only
  worth querying if every edge resolves; that check is cheap and catches
  registry rot that per-file validation misses.

---

## 9. The acceptance test

Before broad content, prove the ontology on four entries that share one schema
with no domain-specific hacks leaking sideways:

| entry | kind | domain | proves |
|---|---|---|---|
| PageRank | algorithm | graph | *(built)* |
| Cosine similarity | measure | similarity | *(built)* non-graph input, a result keyed by pair, and a checkable bound that is a theorem rather than a convention |
| Fellegi-Sunter | statistical_model | entity_resolution | rich `under_determined`, composition, and an output that is hard to verify |
| CSR | *(structure)* | graph | the second root, and honest complexity |

Cosine was the schema test — trivial to verify, so any awkwardness would have
been the schema's fault and not the method's. What it cost: a second dataset
kind with a loader and a profile, one door in front of both, two `Converted*`
shapes saying how results are keyed, and a comparator entry. What it did *not*
cost: a single kind-specific branch inside `run`, `compare` or `verify`. The
awkwardness that did surface was in the *reporting* layer, which had assumed
"dataset" meant "graph" in four places, and in `requirements.py`, where "the
degenerate fixtures" turned out not to be one list. Fellegi-Sunter is the *semantic* test: a
method whose output is barely verifiable but whose choice points (comparison
construction, m/u estimation, thresholds) are the entire substance. If our
`under_determined` machinery carries Fellegi-Sunter, it will carry most things.

**If a method needs a hack, fix the ontology before adding content.**

---

## 10. What this is not

- Not a catalogue of computer science. Expand by *adjacent problem*, never by
  "algorithms we could add".
- Not a replacement for OSSIE, dbt, or a feature store. Gigi describes methods
  and structures; those describe data.
- Not a graph database. The knowledge graph is compiled output.
- Not a reason to loosen anything. Every guarantee in
  [ADR 0005](adr/0005-divergence-claims-must-be-executable.md),
  [0008](adr/0008-machine-readable-first.md) and
  [0009](adr/0009-known-answers-and-the-ladder.md) survives generalisation, or
  the generalisation is wrong.
