# Gigi

**An executable registry of graph algorithm semantics.**

The same named graph algorithm can return different answers on different backends, because their defaults and semantics differ. Gigi writes those differences down, and then runs them, so the write-up cannot quietly become untrue.

Here is one, measured by this repository's own test suite:

```
PageRank, weighted-small, no parameters given

  backend       a          b          c
  reference    0.233918   0.333333   0.432749
  networkx     0.118150   0.400793   0.481057    <- 49% off, silently
  igraph       0.233918   0.333333   0.432749
  rustworkx    0.233919   0.333333   0.432748
```

NetworkX defaults to `weight="weight"`, so it ran *weighted* PageRank. igraph and rustworkx ignore edge weights unless you ask. Nobody warns you, and the ranking you get depends on which library you imported.

## Quick start

Once the first release is published:

```bash
pip install "gigi-algo[all]"
gigi ask "what is PageRank useful for?"
```

To work on Gigi itself, use a checkout instead:

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
gigi promote degree_centrality --dry-run           # has it earned the next tier?
gigi version                                       # build, backends, and which registry
gigi typst pagerank --pdf                          # a printable, citable PDF of the entry
gigi typst pagerank --pdf --review                 # same, with the open questions in the margin
gigi backends                                       # what is installed here
gigi inspect datasets/weighted-small               # cheap structural facts
gigi compare pagerank -g weighted-small --defaults # reproduce the table above
gigi verify pagerank                               # check every claim
gigi site build                                    # render it all as HTML
```

The Python API is the same thing without the terminal:

```python
import gigi

graph  = gigi.load_graph("datasets/weighted-small")
result = gigi.run("pagerank", backend="networkx", graph=graph)

result.requested_parameters   # {'damping': 0.85, 'weight_property': None, ...}
result.effective_parameters   # {'alpha': 0.85, 'weight': 'weight', 'tol': 1e-06, ...}

report = gigi.verify("pagerank")
report.status                 # 'pass'
```

The CLI, the Python API, and any future agent tooling call the same three functions: `run`, `compare`, `verify`. There is no second code path.

## How it works

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) has the diagrams: the three layers, the verify loop, what a result is, and how `gigi ask` decides.
Start there if you want the shape before the detail.

```
methods/pagerank/method.yaml     the claims
        │
        ├── implementations/           one small file per backend
        │
datasets/*/                            small adversarial fixtures
        │
        ▼
gigi verify pagerank                   runs the claims
        │
        ├── backends agree where the registry says they agree, or CI fails
        └── every declared divergence still reproduces, or CI fails
```

Two independent questions, deliberately never mixed:

1. **Agreement.** With every ambiguous parameter pinned, do the backends match the reference implementation? A difference nothing in the registry accounts for is a build failure.
2. **Reproduction.** Does each declared divergence still happen? A divergence that stopped happening is stale documentation, and is also a build failure.

That second check is what turns a backend upgrade into a signal instead of a surprise.

## What is in v0.1

| | |
|---|---|
| Methods | `pagerank`, `degree_centrality`, `connected_components`, `cosine_similarity` |
| Backends | `reference`, `networkx`, `igraph`, `rustworkx`, `scipy`, `sklearn` |
| Fixtures | 11 small adversarial graphs and 3 vector sets, including the degenerate cases of each |
| Divergences | 7, all reproduced by CI |
| Output kinds | `node_score`, `similarity_score`, `partition` |
| Invariants | 12, checked on every backend and fixture |
| Known answers | 35 hand-derived cases the reference must reproduce |
| Problems | 7 questions, including one nothing here answers |
| Families | 17 across 2 domains, covering the roadmap |
| Attribution | three layers: origin, Gigi credits, divergence discovery |

Coming next: `bfs`, which brings path comparison.

### Agreement is a finding too

`connected_components` runs on four backends across eleven fixtures and they **all agree**, including on the empty graph, isolated node, self loop, and duplicate edge.
The same fixtures split three backends three ways on `degree_centrality`.

That is worth recording rather than shrugging at. A registry that only ever captured disagreement would be a bug tracker with extra steps, and "these four libraries agree here" is information nobody had before it was measured. The reason turns out to be in the maths: components are the equivalence classes of reachability, and reflexivity settles the isolated node and the self loop before an implementation gets a chance to be creative.

What the backends *do* disagree about is whether to answer at all. NetworkX raises on a directed graph rather than guessing weak or strong;
rustworkx raises on strong components of an undirected graph, which igraph answers correctly. This is about strictness, not components, so it is recorded
as a choice point and `mode` makes the question explicit.

### Not only graphs

`cosine_similarity` is here for a reason that is not "more content". Everything Gigi does well, including layered provenance, executed invariants,
named choice points, reproduced divergences, and a priced maturity ladder, is about a *method*, not about a graph. Until PR 2b,
that was a claim rather than a fact.

It is now one method's worth of fact. A fixture declares its kind (`graph` or `vectors`); a backend declares what it accepts; a result is keyed by node or by pair. The harness is still three functions and gained no branch on kind.

It found something on its first fixture. A zero vector has no direction, so the cosine of any pair involving one is undefined.
SciPy answers `NaN`,
scikit-learn answers `0.0`, and the reference declines to answer. The scikit-learn convention is the quieter and more dangerous one: a failed embedding
is reported as *known to be dissimilar to everything*, when the truth is that nothing is known about it.

The headline still says *graph algorithm semantics*, and will until the non-graph content is more than one entry. See [ADR 0011](docs/adr/0011-a-dataset-declares-its-kind.md).

## Contributing

Adding an algorithm means adding one directory. You do not touch `gigi/`, and you do not write any tests. The conformance suite is generated
from the registry, so a new directory is covered automatically.

```
methods/<your_method>/
├── method.yaml            what you claim, where it came from, who built it
├── maths.md                  the definition
├── notes.md                  what you measured
└── implementations/
    ├── reference.py          readable oracle, no libraries
    └── networkx.py           ~15 lines: call the backend, record its defaults
```

`methods/_template/` is a **working example**, it implements degree centrality end to end, so you can run it before you change anything, and CI runs it too so it cannot rot. See [CONTRIBUTING.md](CONTRIBUTING.md).

**You do not need to invent a graph algorithm to contribute.** Reporting a divergence, correcting an attribution, or adding an adversarial fixture needs no Python at all, and all three improve a registry whose entire value is being correct.

## Attribution

Four questions, kept separate, because collapsing them into `inventor:` loses most of the truth:

```
who created the algorithm  !=  who implemented it in Gigi
                           !=  who verified it
                           !=  who found the divergence
```

`provenance:` records original authors, the original work, and structured precursors. Use `attribution_notes` for the parts that resist structure.
PageRank is the reason: the 1998 paper names four authors, while the recursive link-ranking idea runs through Pinski & Narin (1976),
Bonacich (1972), and Katz (1953).

`gigi:` records who did the work here, by role, as ids into `people/people.yaml`. Every id must resolve or the tests fail. Profiles show
lineage rather than a score. There is no leaderboard, on purpose.

## Reviewing

Review should be short and confident. `gigi review <algorithm>` splits the work into what a machine already settled and what only a person can:

```
Settled by machine -- you do not need to check these
  spec validates                       pass
  family resolves                      pass  centrality -> Which nodes matter...
  every credited person resolves       pass
  invariants hold on every run         pass  108 assertions
  declared divergences still reproduce pass  2 declared
  ...

Gaps -- not failures, usually the next contribution choice point 'convergence_criterion' has no fixture

By eye -- nothing checks these but you
  1. Does the reference implementation compute what the definition says?
  2. Could someone learn the algorithm from the reference implementation?
  3. Do maths.md and the `maths:` block say the same thing?
  ...
```

That first by-eye item is the one that matters: the reference implementation is the oracle every backend is compared against, so if it is wrong, every green check above it is meaningless. `tests/expected.yaml` is the partial defence -- known answers derived by hand, from the definition, which the reference must reproduce -- and the command prints the definition so you can check the rest.

Maturity is priced. `gigi/requirements.py` says what `frontier`, `emerging` and `stable` each owe, `gigi review` shows exactly what promotion would take, and the test suite refuses an entry claiming a tier it has not earned.

Readability is itself a checked property. `tests/test_readability.py` enforces no module over 400 code lines, docstrings on modules and non-obvious public names,
functions under 120 lines, CLI help text, and a budget on library growth. That keeps "the code is reviewable" from quietly stopping being true.

## Installing a release

```bash
pip install gigi-algo            # library, CLI, reference backend
pip install "gigi-algo[all]"     # plus NetworkX, igraph and rustworkx
```

Releases are tags. `uv version --bump minor`, a changelog section, `git tag`, and the workflow builds, tests on two backend matrices, publishes to PyPI by trusted publishing, and writes the GitHub Release from the changelog -- only after PyPI confirms the version is installable. See [docs/RELEASING.md](docs/RELEASING.md) and [CHANGELOG.md](CHANGELOG.md).

## Does it read your data the way you mean it?

The same column can be the right input to two methods and mean opposite things. PageRank reads an edge weight as **strength**: higher means stronger.
Dijkstra reads it as **cost**: higher is worse. Run both on a column called `distance` and you have asked two contradictory questions
and been told nothing.

```console
$ gigi why pagerank --graph road-distances-small

Answers
  Which nodes are important because other important nodes point at them?

Does not answer
  Which nodes have the most connections?   -> degree_centrality
  What is the cheapest way to get from here to there?   -> nothing here yet

How it reads edge weight
  as strength: higher means stronger

Your data  (road-distances-small)
  ! Column `distance` looks like distance, and this method reads it as
    strength, where higher means stronger. Did you intend to invert it?
```

Without `--graph` that is documentation. With it, it is advice: it reads the columns actually in front of you. `gigi alternatives` and `gigi related` come from the same structure.

## Ask it something

```console
$ gigi ask "how do I find communities in my graph"

Nothing here answers this.
  the question is known: Which nodes belong together, in the sense of being
  more densely connected to each other than to the rest?
  problems/community_grouping.yaml -- no method claims it

Explicitly not for this
  connected_components declares community_grouping out of scope
```

Connected components is what people reach for when they mean communities. Gigi declines, and names the thing it declined to be.

### A model may find, but not speak

Word matching cannot read paraphrase. *"Which nodes matter most"* shares no word with *"important"*, so it used to return degree centrality and silently
drop PageRank. That was a worse answer than the registry contains, while still looking complete.

So a model gets one job: **choosing which entries a question is about**. It picks ids from a catalogue, checks every id against the registry,
and drops anything invented. It cannot add a method to Gigi by mentioning it, and it writes no word you read. Every output sentence is
registry content that CI verifies. It can still choose an unhelpful real entry, which is why Gigi shows the match path and keeps recommendations reviewable.

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY = "..."       # or OPENAI_API_KEY, or run Ollama
gigi ask "who are the influencers in my network"
gigi providers                        # see what is configured
gigi ask "..." --model none           # force word matching
```

```bash
# macOS and Linux
export ANTHROPIC_API_KEY=...           # or OPENAI_API_KEY, or run ollama
gigi ask "who are the influencers in my network"
gigi providers                         # see what is configured
gigi ask "..." --model none            # force word matching
```

`GIGI_MODEL` sets the default provider (`anthropic`, `openai`, `ollama`, or `none`). No key, no network, a timeout, or a model response Gigi cannot use falls back to word matching. `gigi ask` works offline. Every answer says how it was matched, so a model's involvement is never invisible.

### Start from your question

| If you are… | Try this | What you get |
|---|---|---|
| a student learning the vocabulary | `gigi ask "what is PageRank useful for?"` | A verified method, its maturity, and the next command to understand it. |
| a researcher comparing implementations | `gigi compare pagerank -d weighted-small --defaults` | The same method across backends, including the recorded default that changes the answer. |
| a developer with a transaction network | `gigi ask "who are the influencers in my network"` | Model-assisted matching when configured, then registry-backed candidates to inspect with `gigi why`. |
| curious about communities | `gigi ask "how do I find communities in my graph"` | An honest gap: Gigi names community grouping and explains why connected components is not a substitute. |

The third example is deliberately phrased as a normal question rather than a registry keyword. With no configured model it may return no match; use `gigi providers` to see whether a provider is available, or start with `gigi ask "what is PageRank useful for?"` while offline.

See [ADR 0014](docs/adr/0014-a-model-may-find-but-not-speak.md).

## For agents

Gigi supports both directions. `gigi ask` can use a configured model to select registry entries; an external model can call Gigi through MCP to inspect, run, compare, and verify those entries.

```console
$ gigi mcp        # eight tools over MCP on stdio
$ gigi tools -f anthropic   # or openai, or mcp -- the same tools as JSON schemas
```

Add to Claude Code or Claude Desktop:

```json
{"mcpServers": {"gigi": {"command": "gigi", "args": ["mcp"]}}}
```

Agents get `gigi_ask`, `gigi_describe_method`, `gigi_why`, `gigi_list_methods`, `gigi_list_datasets`, and, most importantly, `gigi_run`, `gigi_compare`, and `gigi_verify`.
A model can check a claim before making it. `frontier` methods still refuse to run without opt-in; the harness gate applies to every caller.

## Run it in a container

The published image includes the registry and every supported backend:

```bash
docker run --rm ghcr.io/graphgeeks-lab/gigi-algo:latest ask "which nodes matter most"
docker run --rm ghcr.io/graphgeeks-lab/gigi-algo:latest verify

# The default command starts Gigi's MCP server.
docker run -i --rm ghcr.io/graphgeeks-lab/gigi-algo:latest

# Pass a provider key only when you want model-assisted matching.
docker run --rm -e ANTHROPIC_API_KEY \
  ghcr.io/graphgeeks-lab/gigi-algo:latest ask "who are the influencers in my network"
```

The entrypoint is `gigi`, so subcommands work as arguments. The default command is the MCP server, which lets an agent runtime use Gigi without Python,
uv, or graph libraries installed on the host:

```json
{"mcpServers": {"gigi": {"command": "docker", "args": ["run", "-i", "--rm",
"ghcr.io/graphgeeks-lab/gigi-algo:latest", "mcp"]}}}
```

To build the image from this checkout instead:

```bash
docker build -t gigi .
docker run --rm gigi verify
```

The image ships every backend, so `gigi verify` inside it means what it means outside it. That is most of its size, and an image
that cannot run igraph and rustworkx cannot verify the registry.

Your own registry instead of the bundled one:

```bash
docker run --rm \
  -v "$PWD/methods:/registry/methods:ro" \
  -e GIGI_METHODS_DIR=/registry/methods \
  gigi verify
```

`.github/workflows/docker.yml` builds and smoke-tests on every push. A `v*` tag publishes version, major-minor, and `latest` tags to `ghcr.io/graphgeeks-lab/gigi-algo`.

## Maturity

Every algorithm declares a tier, and the tier has teeth. `frontier` entries **refuse to run** without an explicit `--allow-frontier`, so an agent asking for the best available algorithm can never be handed unverified work silently. `emerging` and `stable` each have a stated price in [`gigi/requirements.py`](gigi/requirements.py); `gigi review` shows where an entry stands and `gigi promote` refuses a tier it has not earned.

[docs/MATURITY.md](docs/MATURITY.md) covers all four tiers, how to move up, and how to use `frontier`.

## Vocabulary

Divergence, invariant, choice point, known answer, reference, maturity -- the words this project leans on are defined once, in plain language, in [docs/GLOSSARY.md](docs/GLOSSARY.md).

## Built for readers who are not people

An agent choosing an algorithm cannot read `maths.md`, and should not be asked to infer facts from prose. So every fact lives in structured form, and prose supplements it rather than carrying it alone:

- **`maths:`**: the definition in plain text and LaTeX, the invariants, and the places the definition leaves a choice open.
- **`invariants`** are *executed*. "Scores sum to one" is two lines of YAML, and it is then asserted on every backend, on every fixture, forever. A property whose id names no check in `gigi/invariants.py` fails the build.
- **`under_determined`** names the choice points, where backends *could* differ, as opposed to `divergences`, which records where they *did*. That is what lets a new backend be assessed before it is ever run.
- **`relationships`** are typed and conditioned. "See also" tells a machine nothing; "generalises eigenvector centrality, and coincides with it as damping approaches 1 on a strongly connected graph" tells it when a substitution is legitimate.
- **`family`** resolves to `families/families.yaml`, where a family is a *question* ("Which nodes matter, and in what sense of matter?") rather than a label.

`gigi export` gives all of it as one JSON document, serialised from the same models the library uses, so what a machine reads
is exactly what `gigi verify` checks.
The one place a language model belongs is turning a person's sentence into a typed intent; everything after that reads structure.

See [ADR 0008](docs/adr/0008-machine-readable-first.md).

## What Gigi is not

Not a graph backend. Not a graph database. Not a query language. Gigi does not implement fast kernels or reimplement NetworkX,
igraph, or rustworkx inside an adapter.
It calls them, records exactly what they did, and tells you where they disagree.

## Licence

Apache-2.0. Fixtures are CC0.
