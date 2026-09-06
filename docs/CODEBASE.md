# Reading this codebase

Most of Gigi is content, not code. `methods/`, `datasets/`, `problems/`, `families/`, `domains/`, `semantics/` and `people/` are the project; `gigi/` is the machinery that reads them and runs them. If you are here to contribute a method, you do not need this file — read [CONTRIBUTING.md](contributing.md) instead.

For the shape of the system before the code — the three layers, the verify loop, how `gigi ask` decides — read [ARCHITECTURE.md](ARCHITECTURE.md) first.

## Read it in this order

Roughly ninety minutes, and you will have seen everything.

| # | File | What you learn |
|---|---|---|
| 1 | `methods/pagerank/method.yaml` | What a registry entry claims. The whole design is visible here before any Python. |
| 2 | `methods/pagerank/implementations/reference.py` | What a reference implementation looks like — the oracle, and a teaching artifact. |
| 3 | `methods/pagerank/implementations/networkx.py` | What a backend implementation looks like. Fifteen lines. |
| 4 | `gigi/models/spec.py` | Every typed object in a registry entry, grouped by concern. Skim the class names first. |
| 5 | `gigi/graph.py` | The neutral data layer: Arrow in memory, CSV on disk, and a deliberately cheap profile. |
| 6 | `gigi/data.py` | One door in front of every fixture, whatever kind it is. Twenty lines that stop everything above it from assuming "dataset" means "graph". |
| 7 | `gigi/registry.py` | How a directory becomes a `MethodSpec`, and how families resolve. |
| 8 | `gigi/backends/networkx.py` | An adapter: installed? version? convert. Nothing else. |
| 9 | `gigi/backends/base.py` | What a converted input owes the harness — including what its result is keyed by, and whether every key is owed an answer. |
| 10 | `gigi/harness.py` | **The heart.** `run`, `compare`, `verify`. Read `verify` slowly — it is the argument the whole project makes. |
| 11 | `gigi/invariants.py` | The maths, executed. |
| 12 | `tests/test_conformance.py` | How a new method gets tested without anyone writing a test. |
| 13 | `gigi/review.py` | What a machine settles versus what a person must. |

If you want the short version of *why the schema is not graph-shaped*, read `methods/cosine_similarity/method.yaml` beside `methods/pagerank/method.yaml`. Two domains, two input kinds, two output kinds, one schema.

Everything else — `cli/`, `site/`, `vectors.py`, `people.py`, `runstore.py`, `paths.py` — is plumbing you can read when you need it.

## The map

```
                 methods/*/method.yaml           the claims
                 datasets/*/                     small adversarial fixtures
                 problems/*.yaml                 the questions
                 families/ · domains/            the taxonomy
                 people/people.yaml              who did the work
                          │
                          ▼
   registry.py ──────► models/ ◄─── data.py ──┬── graph.py
        │                  ▲            │     └── vectors.py
        │                  │            ▼
        │             invariants.py   backends/*.py ──► the libraries
        │                  ▲                 │
        └──────────────────┴─────────────────┘
                          │
                          ▼
                     harness.py            run · compare · verify
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          cli/         site/       review.py
```

Dependencies point one way only. `models.py` imports nothing of ours; `graph.py` and `registry.py` know nothing about backends; adapters know nothing about verification; `harness.py` knows nothing about how results are displayed. If you find yourself wanting an import that points back up this diagram, the code is in the wrong place.

## Two buckets, and why the distinction matters

**Capability** (~2,780 lines) is code that computes something nothing else can: models, registry, the data layer, adapters, harness, results, invariants, people, and the retrieval behind `gigi ask`. Growth here means the system learned a new concept — and that is what the budget in `tests/test_readability.py` guards.

**Reporting** (~2,390 lines) re-presents what capability already computed: the CLI, the static site, the review summary, and `agent/` — the same registry addressed by a model rather than a person. It grows with what we choose to *show*, which is a much cheaper kind of growth, so it is counted separately.

The line is not a loophole. If something in `cli/` or `site/` starts computing rather than formatting, it has moved buckets and belongs in the library.

## Where this is going

[ONTOLOGY.md](ONTOLOGY.md) describes the schema the registry grows into: methods and data structures as two roots meeting at *operations*, the extension rules that keep a general schema from becoming a useless one, and why the semantic layer borrows Apache OSSIE's `ai_context` rather than inventing its own.

Some of it is built. The schema generalised in PR 1, the semantic layer landed in PR 2, and `cosine_similarity` — a measure over vectors, in the `similarity` domain — proved in PR 2b that the runtime generalised with it. Data structures and `operations` are not built. The v0.1 release stays graph-content-led, and the extension rules in that document are the ones the test suite enforces today, not aspirations.

## Rules the tests enforce

`tests/test_readability.py` checks these, so they cannot quietly stop being true:

- no module over **400 code lines** — a reviewer should be able to read a whole file before judging a change to it;
- every module has a docstring saying what it is for, because people arrive from stack traces;
- every public name longer than five lines explains itself;
- no function over 120 lines;
- every CLI command has help text;
- capability stays under its budget.

Docstrings and comments do not count toward any line total. Prose is not what makes a file hard to read.

## Conventions worth knowing before you edit

- **Names are spelled out.** `divergence`, not `div`. `relationship`, not `rel`. The registry is read more than it is written.
- **A failure is a value, not an exception.** `run()` returns a `RunResult` with a status, because verification has to report what did *not* run.
- **Errors name the file.** Validation failures are re-raised with the path attached; the person seeing them is usually editing that file.
- **No abstraction with one implementation.** Adapters are a dict in one file. There is no plugin system, and there should not be until there is a reason.
- **No Pydantic model** unless it crosses a module boundary or is serialised.
- **Comments explain *why*.** The what is in the code; the why is usually a decision, and decisions belong in the [architecture decision records](adr/0001-arrow-in-memory-csv-on-disk.md).
