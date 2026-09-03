# Reading this codebase

Most of Gigi is content, not code. `algorithms/`, `datasets/`, `families/` and
`people/` are the project; `gigi/` is the machinery that reads them and runs
them. If you are here to contribute an algorithm, you do not need this file —
read [CONTRIBUTING.md](../CONTRIBUTING.md) instead.

## Read it in this order

Roughly ninety minutes, and you will have seen everything.

| # | File | What you learn |
|---|---|---|
| 1 | `algorithms/pagerank/algorithm.yaml` | What a registry entry claims. The whole design is visible here before any Python. |
| 2 | `algorithms/pagerank/implementations/reference.py` | What a reference implementation looks like — the oracle, and a teaching artifact. |
| 3 | `algorithms/pagerank/implementations/networkx.py` | What an engine implementation looks like. Fifteen lines. |
| 4 | `gigi/models.py` | Every typed object, one file, grouped by concern. Skim the class names first. |
| 5 | `gigi/graph.py` | The neutral data layer: Arrow in memory, CSV on disk, and a deliberately cheap profile. |
| 6 | `gigi/registry.py` | How a directory becomes an `AlgorithmSpec`, and how families resolve. |
| 7 | `gigi/adapters/networkx.py` | An adapter: installed? version? convert. Nothing else. |
| 8 | `gigi/harness.py` | **The heart.** `run`, `compare`, `verify`. Read `verify` slowly — it is the argument the whole project makes. |
| 9 | `gigi/invariants.py` | The maths, executed. |
| 10 | `tests/test_conformance.py` | How a new algorithm gets tested without anyone writing a test. |
| 11 | `gigi/review.py` | What a machine settles versus what a person must. |

Everything else — `cli/`, `site/`, `people.py`, `runstore.py`, `paths.py` — is
plumbing you can read when you need it.

## The map

```
                 algorithms/*/algorithm.yaml     the claims
                 datasets/*/                     small adversarial graphs
                 families/families.yaml          the taxonomy
                 people/people.yaml              who did the work
                          │
                          ▼
   registry.py ──────► models.py ◄────── graph.py
        │                  ▲                 │
        │                  │                 ▼
        │             invariants.py     adapters/*.py ──► the engines
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

Dependencies point one way only. `models.py` imports nothing of ours;
`graph.py` and `registry.py` know nothing about engines; adapters know nothing
about verification; `harness.py` knows nothing about how results are displayed.
If you find yourself wanting an import that points back up this diagram, the
code is in the wrong place.

## Two buckets, and why the distinction matters

**Capability** (~1,360 lines) is code that computes something nothing else can:
models, registry, graph, adapters, harness, results, invariants, people.
Growth here means the system learned a new concept — and that is what the
budget in `tests/test_readability.py` guards.

**Reporting** (~1,240 lines) re-presents what capability already computed: the
CLI, the static site, the review summary. It grows with what we choose to
*show*, which is a much cheaper kind of growth, so it is counted separately.

The line is not a loophole. If something in `cli/` or `site/` starts computing
rather than formatting, it has moved buckets and belongs in the library.

## Rules the tests enforce

`tests/test_readability.py` checks these, so they cannot quietly stop being
true:

- no module over **400 code lines** — a reviewer should be able to read a whole
  file before judging a change to it;
- every module has a docstring saying what it is for, because people arrive
  from stack traces;
- every public name longer than five lines explains itself;
- no function over 120 lines;
- every CLI command has help text;
- capability stays under its budget.

Docstrings and comments do not count toward any line total. Prose is not what
makes a file hard to read.

## Conventions worth knowing before you edit

- **Names are spelled out.** `divergence`, not `div`. `relationship`, not
  `rel`. The registry is read more than it is written.
- **A failure is a value, not an exception.** `run()` returns a `RunResult`
  with a status, because verification has to report what did *not* run.
- **Errors name the file.** Validation failures are re-raised with the path
  attached; the person seeing them is usually editing that file.
- **No abstraction with one implementation.** Adapters are a dict in one file.
  There is no plugin system, and there should not be until there is a reason.
- **No Pydantic model** unless it crosses a module boundary or is serialised.
- **Comments explain *why*.** The what is in the code; the why is usually a
  decision, and decisions belong in [docs/adr/](adr/).
