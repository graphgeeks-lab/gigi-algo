# Gigi

**An executable registry of graph algorithm semantics.**

The same named graph algorithm can return different answers on different
engines, because their defaults and semantics differ. Gigi writes those
differences down — and then runs them, so the write-up cannot quietly become
untrue.

Here is one, measured by this repository's own test suite:

```
PageRank, weighted-small, no parameters given

  engine       a          b          c
  reference    0.233918   0.333333   0.432749
  networkx     0.118150   0.400793   0.481057    <- 49% off, silently
  igraph       0.233918   0.333333   0.432749
  rustworkx    0.233919   0.333333   0.432748
```

NetworkX defaults to `weight="weight"`, so it ran *weighted* PageRank. igraph
and rustworkx ignore edge weights unless you ask. Nobody warns you, and the
ranking you get depends on which library you imported.

## Quick start

```bash
git clone https://github.com/graphgeeks-lab/gigi-algo
cd gigi-algo
pip install -e ".[dev]"
```

```bash
gigi list                                          # what is in the registry
gigi show pagerank                                 # what the registry claims
gigi maths pagerank                                # definition, invariants, choice points
gigi origin pagerank                               # who created it, who built the entry
gigi families                                      # the taxonomy, as questions
gigi people                                        # who has contributed, and to what
gigi export -o registry.json                       # the whole registry, for machines
gigi review pagerank                               # what to check before merging
gigi typst pagerank --pdf                          # a printable, citable PDF of the entry
gigi typst pagerank --pdf --review                 # same, with the open questions in the margin
gigi engines                                       # what is installed here
gigi inspect datasets/weighted-small               # cheap structural facts
gigi compare pagerank -g weighted-small --defaults # reproduce the table above
gigi verify pagerank                               # check every claim
gigi site build                                    # render it all as HTML
```

The Python API is the same thing without the terminal:

```python
import gigi

graph  = gigi.load_graph("datasets/weighted-small")
result = gigi.run("pagerank", engine="networkx", graph=graph)

result.requested_parameters   # {'damping': 0.85, 'weight_property': None, ...}
result.effective_parameters   # {'alpha': 0.85, 'weight': 'weight', 'tol': 1e-06, ...}

report = gigi.verify("pagerank")
report.status                 # 'pass'
```

The CLI, the Python API, and any future agent tooling call the same three
functions: `run`, `compare`, `verify`. There is no second code path.

## How it works

```
algorithms/pagerank/algorithm.yaml     the claims
        │
        ├── implementations/           one small file per engine
        │
datasets/*/                            small adversarial fixtures
        │
        ▼
gigi verify pagerank                   runs the claims
        │
        ├── engines agree where the registry says they agree, or CI fails
        └── every declared divergence still reproduces, or CI fails
```

Two independent questions, deliberately never mixed:

1. **Agreement.** With every ambiguous parameter pinned, do the engines match
   the reference implementation? A difference nothing in the registry accounts
   for is a build failure.
2. **Reproduction.** Does each declared divergence still happen? A divergence
   that stopped happening is stale documentation, and is also a build failure.

That second check is what turns an engine upgrade into a signal instead of a
surprise.

## What is in v0.1

| | |
|---|---|
| Algorithms | `pagerank`, `degree_centrality` |
| Engines | `reference`, `networkx`, `igraph`, `rustworkx` |
| Fixtures | 9 small adversarial graphs, including `empty` and `single-node` |
| Divergences | 5, all reproduced by CI |
| Output kinds | `node_score` |
| Invariants | 7, checked on every engine and fixture |
| Known answers | 18 hand-derived cases the reference must reproduce |
| Families | 16, covering the roadmap |
| Attribution | three layers: origin, Gigi credits, divergence discovery |

Coming next: `connected_components` and `bfs`, which bring partition and path
comparison. See [PLAN.md](PLAN.md) for the roadmap and for what is deliberately
not being built yet.

## Contributing

Adding an algorithm means adding one directory. You do not touch `gigi/`, and
you do not write any tests — the conformance suite is generated from the
registry, so a new directory is covered automatically.

```
algorithms/<your_algorithm>/
├── algorithm.yaml            what you claim, where it came from, who built it
├── maths.md                  the definition
├── notes.md                  what you measured
└── implementations/
    ├── reference.py          readable oracle, no libraries
    └── networkx.py           ~15 lines: call the engine, record its defaults
```

`algorithms/_template/` is a **working example** — it implements degree
centrality end to end, so you can run it before you change anything, and CI runs
it too so it cannot rot. See [CONTRIBUTING.md](CONTRIBUTING.md).

**You do not need to invent a graph algorithm to contribute.** Reporting a
divergence, correcting an attribution, or adding an adversarial fixture needs no
Python at all, and all three improve a registry whose entire value is being
correct.

## Attribution

Four questions, kept separate, because collapsing them into `inventor:` loses
most of the truth:

```
who created the algorithm  !=  who implemented it in Gigi
                           !=  who verified it
                           !=  who found the divergence
```

`provenance:` records original authors, the original work, and structured
precursors — with `attribution_notes` for the parts that resist structure.
PageRank is the reason: the 1998 paper names four authors, while the recursive
link-ranking idea runs back through Pinski & Narin (1976), Bonacich (1972) and
Katz (1953).

`gigi:` records who did the work here, by role, as ids into
`people/people.yaml`. Every id must resolve or the tests fail. Profiles show
lineage rather than a score — there is no leaderboard, on purpose.

## Reviewing

Review should be short and confident. `gigi review <algorithm>` splits the work
into what a machine already settled and what only a person can:

```
Settled by machine -- you do not need to check these
  spec validates                       pass
  family resolves                      pass  centrality -> Which nodes matter...
  every credited person resolves       pass
  invariants hold on every run         pass  108 assertions
  declared divergences still reproduce pass  2 declared
  ...

Gaps -- not failures, usually the next contribution
  - choice point 'convergence_criterion' has no fixture

By eye -- nothing checks these but you
  1. Does the reference implementation compute what the definition says?
  2. Could someone learn the algorithm from the reference implementation?
  3. Do maths.md and the `maths:` block say the same thing?
  ...
```

That first by-eye item is the one that matters: the reference implementation is
the oracle every engine is compared against, so if it is wrong, every green
check above it is meaningless. `tests/expected.yaml` is the partial defence --
known answers derived by hand, from the definition, which the reference must
reproduce -- and the command prints the definition so you can check the rest.

Maturity is priced. `gigi/requirements.py` says what `frontier`, `emerging` and
`stable` each owe, `gigi review` shows exactly what promotion would take, and the
test suite refuses an entry claiming a tier it has not earned.

Readability is itself a checked property. `tests/test_readability.py` enforces
no module over 400 code lines, a docstring on every module and every non-obvious
public name, no function over 120 lines, help text on every CLI command, and a
budget on library growth — so "the code is reviewable" cannot quietly stop being
true. See [docs/REVIEWING.md](docs/REVIEWING.md) and
[docs/CODEBASE.md](docs/CODEBASE.md), which has a ninety-minute reading order
for the whole codebase.

## Design decisions

The short version lives in [docs/adr/](docs/adr/):

- [Arrow in memory, CSV on disk](docs/adr/0001-arrow-in-memory-csv-on-disk.md) — fixtures must be reviewable in a diff
- [Reference implementations optimise for readability](docs/adr/0002-reference-optimises-readability.md)
- [The graph data contract](docs/adr/0003-graph-data-contract.md) — nulls rejected, duplicates and self loops preserved
- [Engine defaults are never hidden](docs/adr/0004-engine-defaults-are-never-hidden.md)
- [Divergence claims must be executable](docs/adr/0005-divergence-claims-must-be-executable.md)
- [Maturity gates strictness](docs/adr/0006-maturity-gates-strictness.md)
- [Attribution has layers](docs/adr/0007-attribution-has-layers.md) — never a single `inventor:` field
- [Machine-readable first](docs/adr/0008-machine-readable-first.md) — the next reader may not be a person

## Built for readers who are not people

An agent choosing an algorithm cannot read `maths.md`, and should not be asked
to infer facts from prose. So every fact lives in structured form, and prose
supplements it rather than carrying it alone:

- **`maths:`** — the definition in plain text and LaTeX, the invariants, and
  the places the definition leaves a choice open.
- **`invariants`** are *executed*. "Scores sum to one" is two lines of YAML,
  and it is then asserted on every engine, on every fixture, forever. A
  property whose id names no check in `gigi/invariants.py` fails the build.
- **`under_determined`** names the choice points — where engines *could*
  differ, as opposed to `divergences`, which records where they *did*. That is
  what lets a new engine be assessed before it is ever run.
- **`relationships`** are typed and conditioned. "See also" tells a machine
  nothing; "generalises eigenvector centrality, and coincides with it as
  damping approaches 1 on a strongly connected graph" tells it when a
  substitution is legitimate.
- **`family`** resolves to `families/families.yaml`, where a family is a
  *question* ("Which nodes matter, and in what sense of matter?") rather than a
  label.

`gigi export` gives all of it as one JSON document, serialised from the same
models the library uses — so what a machine reads is exactly what
`gigi verify` checks. The one place a language model belongs is turning a
person's sentence into a typed intent; everything after that reads structure.
See [ADR 0008](docs/adr/0008-machine-readable-first.md).

## What Gigi is not

Not a graph engine. Not a graph database. Not a query language. Gigi does not
implement fast kernels and it never reimplements NetworkX, igraph or rustworkx
inside an adapter — it calls them, records exactly what they did, and tells you
where they disagree.

## Licence

Apache-2.0. Fixtures are CC0.
