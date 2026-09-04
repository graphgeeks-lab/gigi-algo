# Contributing

The most valuable contribution is an algorithm with its backend implementations and an honest account of where the backends disagree. That takes one directory and no test-writing.

## Setup

```bash
git clone https://github.com/graphgeeks-lab/gigi-algo
cd gigi-algo
pip install -e ".[dev]"
pytest
```

Backends are optional extras. If you only have NetworkX installed, the suite skips igraph and rustworkx rather than failing — you can contribute usefully without installing all four.

```bash
pip install -e ".[networkx]"          # just one
pip install -e ".[all]"               # all four
```

## The words

If *divergence*, *invariant*, *choice point* or *known answer* are not yet
obvious, read [docs/GLOSSARY.md](docs/GLOSSARY.md) first -- five minutes, and
everything below will make sense.

## Add yourself first

If you are contributing anything that gets credited, a spec, an implementation, a divergence — add yourself to `people/people.yaml`:

```yaml
- id: your-handle
  name: Your Name
  github: your-handle
  orcid: null
  interests: [graph_algorithms]
  linkedin: your-handle
  links: {mastodon: "https://..."}    # anything without a named field
  roles: [spec-curator, reference-author]
```

Every id referenced from an algorithm must resolve, or the test suite fails. There is no score and no leaderboard: a profile shows which algorithms you worked on, which artifacts you wrote, and which divergences you found.

## Adding an algorithm

```bash
cp -r methods/_template methods/betweenness_centrality
```

The template is a **working example** — degree centrality, running end to end. Run it first, then replace it a piece at a time.

**1. Fill in `method.yaml`.** Nothing needs registering anywhere else; the directory *is* the registration. Set `maturity: emerging` to start.

**1b. Fill in `provenance:` and `gigi:`.** These answer two different questions and must not be merged.

```yaml
provenance:                        # who created the algorithm
  introduced: 1959
  original_authors:
    - name: Edsger W. Dijkstra
  original_work:
    title: "A note on two problems in connexion with graphs"
    year: 1959
    doi: 10.1007/BF01386390
  precursors: []
  attribution_notes: >
    Independent discoveries, contested credit, later generalisations.

gigi:                              # who did the work here
  spec_curators: [your-handle]
  reference_implementation: [your-handle]
  adapter_contributors:
    networkx: [someone-else]
```

Resist `inventor: <one name>`. Most algorithms have precursors and independent discoveries, and the famous name is rarely the whole story — put the messy part in `attribution_notes` rather than flattening it away. A `stable` algorithm must have original authors and an original work, and CI checks it.

Getting an attribution *right* is a real contribution, and one that needs no Python.

**1b-ii. Name the problem, and the ones you are mistaken for.**

A problem is a question stated without reference to any method, in
`problems/<id>.yaml`. Name the ones you solve, and -- more useful to a reader --
the ones people will reach for you by mistake:

```yaml
problems:
  - recursive_node_influence

intent:
  not_for:
    - simple_node_importance      # they mean "most connections"
    - cheapest_route              # they mean "shortest path"
```

`gigi why` prints those questions under *does not answer*, with whatever does
answer them. A method that names no problem cannot be recommended, and
`emerging` requires one.

**1b-iii. Say how you read your input.**

The part nothing else in the ecosystem does. If any value your method consumes
is open to interpretation, say what you make of it:

```yaml
parameters:
  - name: weight_property
    semantic_role: strength         # or: cost, capacity, probability...
    interpretation:
      higher_means: stronger

semantic_interpretations:
  - id: weighted_edge_strength
    subject: edge_weight
    semantic_role: strength
    higher_means: stronger
    description: >
      A larger edge value produces a stronger transition probability.
    common_domain_meanings:
      - meaning: relationship_strength
        fit: strong
      - meaning: distance
        fit: dangerous
        note: >
          Backwards: a 100 km edge would be read as a hundred times stronger
          than a 1 km edge.
```

`gigi why <method> --graph <data>` then compares that against the columns a
user actually has, and asks. Meanings come from
`semantics/column_meanings.yaml`; a meaning not in that file can never be
inferred, and the test suite says so. Mark a reading `dangerous` only with a
note explaining why -- an alarm without a reason gets ignored.

**1c. Fill in `maths:` and pick a `family:`.**

`maths.md` is prose for people; the `maths:` block is the same content in a form a verifier or an agent can use. Both, not either.

```yaml
maths:
  summary: >
    One sentence: what does it compute?
  definition:
    statement: |
      Plain text that renders in a terminal.
    latex: 'C(v) = \frac{\deg(v)}{n - 1}'

  invariants:                       # these are EXECUTED, on every backend
    - id: scores_non_negative       # must name a check in gigi/invariants.py
      statement: "C(v) >= 0 for every v"
      check: true

  under_determined:                 # where backends could differ
    - id: degree_direction
      question: On a directed graph, does "degree" mean in, out, or both?
      choices: [both, in-degree only, out-degree only]
      datasets: [tiny-directed]       # what settles which answer they chose
```

Invariants are the best value in the whole file. Two lines of YAML get asserted on every backend, on every fixture, forever. If the property you want is not in `gigi/invariants.py`, add it — one function and one line in `CHECKS`.

`under_determined` is where you think *before* running anything: name the places the definition leaves a choice, and you have written the test plan for the divergences you are about to look for.

`family:` must be an id from `families/families.yaml`. A family is a question, not a label — if your algorithm does not answer the family's question, it is in the wrong family, and if no family fits, propose one.

**1d. Add `relationships:`.**

Typed edges, not a "see also" list. Pointing at an algorithm nobody has written yet is fine — that is how the roadmap gets recorded.

```yaml
relationships:
  - kind: generalizes           # generalizes | specializes | equivalent_under
    algorithm: eigenvector_centrality   # alternative_to | builds_on | used_by | dual_of
    condition: >
      When damping approaches 1 on a strongly connected graph.
```

If the other algorithm exists, the relationship must be mirrored there with the inverse kind, and CI checks it. `equivalent_under` without a `condition` is rejected: an unconditioned equivalence claim is not usable.

**2. Write `implementations/reference.py`.** No backend libraries, no vectorisation. It should read like `maths.md`. It is the oracle every backend is checked against, so correctness matters and speed does not.

```bash
gigi run betweenness_centrality --graph tiny-directed --backend reference
```

**3. Add backends one at a time.** Each file is a few lines: call the backend, and record what it actually used.

```python
def run(graph, params):
    import networkx as nx
    effective = {"normalized": True, "weight": None, "k": None}
    return nx.betweenness_centrality(graph.native, **effective), effective
```

`effective` is not optional bookkeeping. A backend default nobody wrote down is a backend default nobody can audit, and those defaults are the entire reason this project exists.

**4. Compare.**

```bash
gigi compare betweenness_centrality --graph tiny-directed
```

**5. When backends disagree, find out why.** Then either fix your implementation, or,  if the backends genuinely differ — record it as a
divergence with a `detect` block, so CI reproduces the claim on every run:

```yaml
divergences:
  - id: networkx-normalized-default
    category: default
    severity: medium
    backends: [networkx]
    summary: >
      NetworkX normalises betweenness by default; igraph does not.
    consequence: >
      Scores differ by a factor of (n-1)(n-2)/2 with no warning.
    detect:
      datasets: [tiny-directed]         # every fixture it reproduces on
      backends: [reference, networkx]    # baseline first, subject second
      parameters: {}                    # {} means "backend defaults"
      expect: differ                    # differ | match | error
```

**When they agree, say so in `notes.md`.** Verified agreement is a real result. "All four backends redistribute dangling mass uniformly, checked to 1e-13" is information somebody currently has to rediscover by hand.

**6. Write `tests/expected.yaml` -- the one test file you write, in YAML.**

Every other test compares backends against your reference implementation. If the reference is wrong, they all pass anyway. Known answers are the guard:

```yaml
cases:
  - id: undirected_triangle_is_uniform
    derived: Symmetry; every node in a triangle has degree 2, and n - 1 = 2.
    graph:
      directed: false
      edges: [[a, b], [b, c], [c, a]]
    parameters: {normalized: true}
    expected: {a: 1.0, b: 1.0, c: 1.0}
```

`derived` is required and is the point: it says where the number came from -- symmetry, a closed form, a hand count, a worked example in a paper. Never "I ran  the code". A case derived by running the code checks the code against itself. Name a `dataset:` instead of an inline `graph:` when you want the case to run on every backend too. `emerging` needs two cases; `stable` needs four.

**7. Run the suite.**

```bash
pytest
```

Every test that applies to your algorithm was generated from the files you just wrote. You add none.

## What each maturity requires

One price list, in `gigi/requirements.py`. `gigi review <algorithm>` shows which requirements you meet and exactly what the next tier would take; the test suite refuses an entry that claims a tier it has not earned.

| tier | owes |
|---|---|
| `frontier` | a reference implementation; family and people resolve |
| `emerging` | the maths is stated; one invariant asserted on every run; two known answers, each with a real `derived`; divergences credited; `notes.md` says what was measured |
| `stable` | every divergence has a `detect` block and a matching choice point in `maths.under_determined`; four known answers; original authors and work cited; runs on `empty` and `single-node`; two backends besides the reference |

Start at `emerging` -- or `frontier` if the work is exploratory, which keeps it
out of everything until someone opts in with `--allow-frontier`.

```bash
gigi review <algorithm>              # what this tier requires, and the next
gigi promote <algorithm> --dry-run   # would it pass?
gigi promote <algorithm>             # check, then edit method.yaml
```

`gigi promote` refuses a tier the entry has not earned, and only ever moves up.
Passing is necessary, not sufficient: the changelog line, a second reader and
the commit are yours. Full detail in [docs/MATURITY.md](docs/MATURITY.md).

## Typeset it

```bash
gigi typst <algorithm>          # writes site/typst/<algorithm>.typ
gigi typst <algorithm> --pdf    # needs: pip install 'gigi-algo[docs]'
gigi typst <algorithm> --review # the gaps as margin notes, plus a reviewer checklist
```

A printable, citable version of the entry -- maths rendered from the same LaTeX the spec stores, with the verification evidence attached.

## Adding a dataset

Fixtures are CSV so they can be reviewed in a diff. A good one is small and exists to answer a specific question.

```
datasets/<id>/
├── graph.yaml     directedness, column names, features, expected counts
├── edges.csv      source,target[,weight]
└── nodes.csv      optional; needed only for nodes with no edges
```

`expected.nodes` and `expected.edges` are checked on load, and the flags under `features` are checked against the computed profile — so a fixture that does not match its own description fails immediately.

Write the `description` as the reason it exists. "Directed graph with two sink nodes, because rank held by a node with no outgoing edges has to go somewhere" is useful; "test graph 3" is not.

## Adding a backend

Rarer, and it touches `gigi/`. One file in `gigi/backends/` with `available()`, `version()` and `convert()`, plus a line in `gigi/backends/__init__.py`. Conversion happens once per backend; per-algorithm calls stay beside the
algorithm.

## What we will push back on

- **A divergence without a `detect` block, on a `stable` algorithm.** An untestable claim rots. CI enforces this.
- **A new abstraction with one implementation.** Ask which existing thing it replaces. If the answer is "nothing yet", it is too early.
- **Backend logic in `implementations/<backend>.py`.** If there is a loop over nodes, it belongs in `reference.py`.
- **A Pydantic model that never crosses a module boundary and is never serialised.** Return a plain value.
- **A fixture in Parquet that could have been CSV.** We need to see the diff.
- **A `maths:` block with no checkable invariant, on a `stable` algorithm.** If nothing about the output can be asserted, say why in a note.
- **`equivalent_under` with no condition**, or a `family:` that is not in `families/families.yaml`.
- **`inventor: <one name>`, or a Gigi contributor listed as an original author.** The layers stay separate; CI fails if a name appears in both.

### If your method does not take a graph

Most of the guide above assumes a graph, because most of the registry is
graphs. Nothing in the process changes if yours is not — but two extra things
have to exist before your entry can, and both are cheap:

- **A dataset kind that can hold your input.** `graph` and `vectors` exist. A
  new one needs a metadata model, a loader that validates the file against that
  metadata, a profile, and a `Converted*` that says how results are keyed. See
  `gigi/vectors.py`, which is the whole pattern in under a hundred lines.
- **An output kind with a comparator.** `node_score` and `similarity_score`
  exist. A new one fails the build until `results.py` can judge two of them —
  the same rule as an invariant that names no check.

If your method needs neither, you are adding content and not schema, which is
the easy case. If it needs both, say so in the pull request: it is a bigger
change than a method, and worth reviewing as one.

`gigi/` has a size budget, and `tests/test_readability.py` enforces it along with the rest of the readability rules: no module over 400 code lines, a docstring on every module and every non-obvious public name, no function over 120 lines, help text on every CLI command.

The budget covers **capability**, code that computes something nothing else can (models, registry, the data layer, adapters, harness, results, invariants, people). That is 2,800 lines, currently 2,784. **Reporting**, the CLI, the site, the review summary, is counted separately, because it grows with what we choose to show rather than with what the system understands. The line is not a loophole: if something in `cli/` or `site/` starts computing rather than formatting, it has moved buckets.

New here? [docs/CODEBASE.md](docs/CODEBASE.md) has a reading order that gets you through the whole thing in about ninety minutes. It is a budget, not a law, but a pull request that grows it noticeably should say what it bought.

## Before you open the pull request

```bash
gigi review <your_algorithm>
```

Paste the output into the description. It tells the reviewer what they do *not* need to check by hand, which is most of it — and leaves them free to spend their attention on the handful of things only a person can settle. The reviewer's side of this is [docs/REVIEWING.md](docs/REVIEWING.md).

## Releasing

Maintainers only. `uv version --bump minor`, sync the citation, write the
changelog section, tag. The workflow does the rest and refuses to guess.
[docs/RELEASING.md](docs/RELEASING.md) has the five commands and the one-time
PyPI setup.

## Pull requests

- One algorithm, one dataset, or one fix per pull request.
- `pytest` must pass.
- If you found a divergence, put the numbers in the description. That is the
  interesting part.
- Commit messages: what changed and why, not how.
