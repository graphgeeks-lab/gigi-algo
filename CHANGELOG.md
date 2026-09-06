# Changelog

Every release has a section here, and the release workflow refuses to publish a version this file does not describe. The section for a version becomes its GitHub Release notes, verbatim, so write it for someone deciding whether to upgrade -- what changed, what it means for them, what they need to do.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-09-05

The first version that proves the thesis: the same named algorithm gives different answers on different backends, and a registry can show that with reproducible evidence.

It also stopped being only about graphs. The schema, the data layer and the result types were generalised until a similarity measure over vectors and a partition over components both fit without a special case, and an agent surface was added so a model can call the harness rather than guess at it.

### The short version

| | |
|---|---|
| Methods | `pagerank`, `degree_centrality`, `connected_components`, `cosine_similarity` |
| Backends | reference, networkx, igraph, rustworkx, scipy, sklearn |
| Domains | graph, similarity |
| Output kinds | `node_score`, `similarity_score`, `partition` |
| Divergences | 7, every one reproduced by CI |
| Invariants | 12, executed on every backend and fixture |
| Known answers | 35, each derived by hand rather than observed |
| Fixtures | 11 graphs, 3 vector sets |
| Surfaces | CLI, static site, PDF, MCP server, JSON export |

---

### Added
- **The matching prompt, tuned against the live OpenAI API.** Three fixes, each found by running it rather than reasoning about it:
  - The catalogue rendered entries as `- [problem] community_grouping: ...`, and models duly returned `"problem"` as an id — correct ids alongside it, but a junk entry every time. The id is now the first token on the line. Format is prompt.
  - No `temperature` was set, so a *matching* task ran non-deterministically and the same question gave different answers between runs. Pinned to 0 for OpenAI and Anthropic.
  - The instruction to avoid stretching for a match made the model too conservative; it now returns every plausible candidate and lets Gigi's own filters decide, because a missing entry cannot be recovered downstream.
- **A method can no longer substitute itself for a question it disclaims.** Asked "how do I find communities", a model returns the right question, the method people mistake for it, *and* a second reading that method legitimately answers — so connected components answered via the back door. When the best reading of a question has no method at all, no method that declares it out of scope may be offered instead. Narrow on purpose: when the top question *is* answered, a disclaimer means only "not this particular problem", and PageRank still answers "which nodes are most important" alongside degree centrality.
- **`gigi ask` can use a model to find the right entries** -- and only to find them. Word overlap cannot read paraphrase: *"which nodes matter most"* shares no token with *"important"*, so it returned degree centrality and silently dropped PageRank. With a model, it returns both.
  - The model picks ids from a catalogue of what exists; every id is validated against the registry and anything invented is dropped. It cannot add a method to Gigi by mentioning it, and it writes no word a user reads.
  - Providers: `anthropic`, `openai` (and anything speaking its API -- `OPENAI_BASE_URL` covers vLLM, llama.cpp, LM Studio), `ollama` for local models where nothing may leave the machine. Raw HTTP, no new dependencies.
  - `--model auto|none|<provider>`, `GIGI_MODEL` for the default, and `gigi providers` to see what is configured.
  - Every failure degrades to word matching: no key, no network, a timeout, unparseable JSON, every id invented. `gigi ask` works offline.
  - Every answer prints how it was matched, so a model's involvement -- or a silent fallback -- is never invisible. See [ADR 0014](docs/adr/0014-a-model-may-find-but-not-speak.md), which amends ADR 0013.
- **A container image.** `docker build -t gigi .` today; published to `ghcr.io/graphgeeks-lab/gigi-algo` for `linux/amd64` and `linux/arm64` on the first `v*` tag, which has not happened yet.
  - `ENTRYPOINT` is `gigi`, so every subcommand works as an argument: `docker run --rm gigi verify`, `docker run --rm gigi ask "..."`.
  - The default command is `mcp`, because an agent runtime starting a server is the case a container helps most. `docker run -i --rm gigi` is a working MCP server with no Python, uv or graph libraries on the host.
  - Ships `[all]`, so every backend is present and `gigi verify` inside the image means what it means outside it. That is most of the 617 MB, and the alternative is an image that cannot do the one thing Gigi is for.
  - Runs as a non-root user; a healthcheck that reads the registry rather than just reporting a version.
  - Bring your own registry with `-v` and `GIGI_METHODS_DIR` — the environment overrides in `gigi/paths.py` all work in the image.
  - CI builds and smoke-tests on every push: registry completeness, all six backends, `gigi verify`, non-root, and an MCP handshake plus tool call. Only a tag publishes.
- **An agent surface, and `gigi ask`.** Gigi is now a tool a model can call, rather than a thing that calls a model.
  - **`gigi ask "..."`** answers from the registry and nothing else. No model, no network, no API key. Where nothing here answers the question it says so; where the question is known but unsolved (*"how do I find communities"*) it says that too, and names the methods that declare it out of scope.
  - **`gigi mcp`** serves eight tools over MCP on stdio — hand-rolled JSON-RPC, no new dependency. Drop into Claude Code or Claude Desktop with `{"mcpServers": {"gigi": {"command": "gigi", "args": ["mcp"]}}}`.
  - **`gigi tools --format mcp|anthropic|openai`** emits the same tools as JSON schemas for any other runtime.
  - Agents can execute: `gigi_run`, `gigi_compare` and `gigi_verify` do real work, because a registry an agent can only read is a document. `frontier` methods still refuse to run without opt-in — the gate is in the harness, so an agent inherits it like every other caller.
  - `gigi ask --format context` emits grounded prompt material with the instruction attached, for a model running elsewhere.
  - `aliases:` has been declared on every method since v0.1 and read by nothing. Retrieval is its first consumer. See [ADR 0013](docs/adr/0013-gigi-ask-does-not-generate.md) for why `ask` retrieves rather than generates.
- **`connected_components`**, and with it `partition` — the first output kind that is not one number per key.
  - Four backends, eleven fixtures, forty-four runs, and **zero divergences**. That is the finding: the same fixtures that split three backends three ways on `degree_centrality` produce identical answers here, because the equivalence-relation definition settles the multigraph cases by reflexivity. Measured agreement is evidence too.
  - `PartitionResult` and `compare_partitions`. The four backends label components four different ways — igraph in reverse topological order, rustworkx in reverse index order — so comparing labels would report four correct implementations as four different answers. The comparator compares groupings; the normaliser canonicalises labels to `c0, c1, …` and the maths says why they were never meaningful.
  - `mode: weak | strong`, the ambiguity at the centre of this method. NetworkX and rustworkx refuse a directed graph rather than choosing; igraph defaults to weak. Gigi makes it a parameter and every adapter records which function it actually called.
  - `components_are_connected` and `components_are_maximal` — together a *characterisation*, not a necessary condition: exactly one partition satisfies both, so passing them means passing the definition.
  - `CheckContext`, so an invariant can see the dataset and the effective parameters. "Every component is connected" is a claim about a partition and the graph it partitions; "maximal" means something different under `strong` than under `weak`. See [ADR 0012](docs/adr/0012-a-result-is-not-always-a-number.md).
  - `expected_components` in known answers, for expectations that are groupings.
  - `problems/component_membership.yaml`, and `problems/community_grouping.yaml` — which nothing answers, and which `connected_components` names in `not_for`, because "cluster the graph" almost never means components.
  - `datasets/two-clusters-directed`, whose strong condensation is a real DAG.
- **The first method that is not about graphs** (PR 2b). `cosine_similarity`, across a reference implementation, SciPy and scikit-learn. It exists to falsify the claim ADR 0010 made and could not test: that the schema had stopped being graph-shaped.
  - `datasets/<id>/dataset.yaml` now declares `kind:` — `graph` or `vectors` — discriminated the same way a method's `inputs` are. `gigi/data.py` is the one door: ask for a fixture by id, get whichever container fits.
  - `gigi/vectors.py`: a `VectorData` container, a CSV loader that validates against the metadata, and a profile. Ids containing `|` are refused, because results are keyed `a|b`.
  - Two vector backends, `scipy` and `sklearn`. A backend is not "a graph library"; it is whatever can be handed a dataset and asked for an answer. Each declares what it accepts, and refuses the rest by name.
  - `similarity_score` — an output kind keyed by canonical pair rather than by node — with the comparator the extension rule demands.
  - Two new invariants: `scores_in_signed_unit_interval` (Cauchy-Schwarz, executed) and `keys_are_canonical_pairs`.
  - Fixtures `vectors-small`, `vectors-with-zero`, `vectors-single`; the `similarity` domain, the `vector-similarity` family, and the `pairwise_vector_similarity` problem.
  - **Two divergences on the first fixture.** A zero vector has no direction, so the cosine of any pair involving one is undefined. SciPy returns `NaN`, scikit-learn returns `0.0`, and the reference declines the pair. The scikit-learn convention is the quieter and the worse: a failed embedding is reported as *known to be dissimilar* rather than *no answer*.
- **The semantic layer** (PR 2 of the generalisation). The registry now knows not just what a method computes but what it *assumes about your data*.
  - `problems/` — questions stated without reference to any method. A method names the problems it solves and, more usefully, the ones it is commonly mistaken for.
  - `semantic_role` and `interpretation` on parameters. PageRank reads an edge weight as *strength* (higher is a stronger relationship); Dijkstra will read the same column as *cost* (higher is worse).
  - `semantic_interpretations` on a method: how it reads each part of its input, and which real-world meanings fit, are contextual, or are backwards.
  - `semantics/column_meanings.yaml` — a hint vocabulary, kept as data, that guesses what a column holds from its name.
  - Structured `use_cases`, with the `input_mapping` that is the part that goes wrong.
  - `ai_context` in Apache OSSIE's shape, so anything already reading an OSSIE `ai_context` reads ours.
- **`gigi why <method> [--graph …]`** — what a method answers, what it does not, how it reads its input, and with `--graph`, what it will make of the columns actually in front of you. Without the flag it is documentation; with it, it is advice.
- **`gigi alternatives`**, **`gigi related`**, **`gigi problems`**, **`gigi problem <id>`**.
- `datasets/road-distances-small`, whose weight column is called `distance` and means one.

### Fixed
- `.env` was not in `.dockerignore`, so it entered the Docker build context. Nothing in the Dockerfile copied it, but the daemon received it and one careless `COPY . .` would have shipped live API keys in an image. Secrets are now excluded explicitly.
- A tool result used `error` for both "the tool call failed" and "the run reported a backend failure", so a legitimate result was flagged to the model as a malfunction. The run's own field is now `status_detail`.
- A known-answer case with `expected: {}` asserted nothing at all — the comparison loop had nothing to iterate and passed whatever the backend returned, so `empty_graph_is_empty` had been a no-op since it was written. An empty expectation now asserts that the result is empty.
- The wheel shipped without `problems/` and `semantics/`, so an installed package could not resolve a problem id or read the column-meaning vocabulary — everything PR 2 added was missing outside a checkout. The content directories are now listed once, in `gigi/paths.py`, and the packaging test checks `pyproject.toml` against that list rather than against a copy of it.
- `test_compiles_to_pdf` compiled one entry, so a `latex:` field that mitex cannot render under Typst 0.15 (`\langle`) reached a PDF build rather than CI. Every entry is now typeset in the suite.
- The backends were passed the *dataset's* weight column name, which only worked while every fixture happened to call its column `weight`. On `road-distances-small` igraph looked for an edge attribute named `distance` that the adapter had never created. Adapters now declare the attribute name they used (`ConvertedGraph.weight_attribute`) and implementations ask for it.

### Changed
- The capability budget is 3,000 -- the fifth raise in five releases. A number that only ever goes up measures nothing, so there is now a second check that cannot be satisfied by raising it: capability lines **per shipped method**, which has to fall as the registry grows.
- Removed `gigi.algorithm`, `gigi.algorithms` and `gigi.inspect_graph` — three duplicate names for functions that already had canonical ones, kept for a v0.1 that never shipped. Use `method`, `methods` and `inspect`.
- The capability budget is 2,800, raised from 2,700 for `ask.py`. Fourth raise in four PRs; PLAN.md now carries the argument *against* itself as well as for.
- `gigi run` renders a partition as its groups rather than a score table, and `gigi compare` reports shape and regrouped-node count instead of a top key and a numeric error.
- The capability budget is 2,700, raised from 2,400. Third raise in three PRs; PLAN.md argues it should be the last.
- `gigi run` and `gigi compare` take `--dataset/-d`; `--graph/-g` still works. `gigi datasets` gained a `kind` column and reports shape per kind.
- `gigi review` no longer suggests writing a NetworkX implementation of a vector measure, or running a graph algorithm against a vectors fixture. Gaps are computed from what the method can actually consume.
- The capability budget is 2,400, raised from 2,100 for the data layer. PLAN.md says what it bought.
- `models.py` passed 400 code lines and so became a package (`people`/`spec`/`data`/`execution`), which is the rule it was always going to hit. `from gigi.models import X` is unchanged.
- The CLI gained `explain.py`, splitting "what does the registry hold" from "what does this mean for me".
- `problem:` on a method is now `summary:`; the *question* lives in the problem it names. `intent.solves` is gone — the free-text phrasings moved to `ai_context.synonyms`, and `intent.not_for` now names problems rather than prose.
- `Relationship.algorithm` is `Relationship.method`.
- **The schema is no longer graph-shaped** (PR 1 of the generalisation, [ADR 0010](docs/adr/0010-general-schema-narrow-content.md)). Content stays graph-only; the shape underneath does not assume it.
  - `AlgorithmSpec` is now `MethodSpec`, with a required `kind` (`algorithm` | `measure` | `statistical_model` | `heuristic` | `procedure`
    | `solver`).
  - `requirements:` is now `inputs:`, a union discriminated on `kind`, so a method can consume something other than a graph.
  - `engines:` is now `backends:`, and `EngineAdapter` is `BackendAdapter`. NetworkX is a graph engine; scikit-learn and Splink are not.
  - `algorithms/` is now `methods/`, flat, with `algorithm.yaml` renamed to `method.yaml`. Grouping is by domain, for display only.
  - Families belong to a domain (`domains/domains.yaml`), and a method's domain is *derived* through its family rather than stored on the method.
  - `comparison.kind` is gone: which comparator runs follows from `output.kind`, and two fields naming one fact drift apart.
  - `OutputKind` is pruned to the kinds that have a comparator. A kind without one describes a method nothing can verify, and the test suite now refuses it — the same rule as an invariant that names no check.
  - Unknown keys in an input spec are rejected rather than silently ignored.
  - `gigi list` gained `--domain` and `--kind`; `gigi.method()` joins `gigi.algorithm()`.

  No behaviour changed. A before/after fingerprint of every run, comparison, invariant and divergence check across both methods, all backends and all nine fixtures is identical except for the word "engines" becoming "backends" in one sentence of the verification conclusion.

### Added
- `gigi version`, showing the build, the backend versions and **which registry** is being read -- a checkout or the copy packaged in the wheel.
- `gigi promote`, which re-checks every requirement of the target tier and refuses one that has not been earned. It only moves up the ladder.
- The `frontier` tier is now enforced, not labelled: those algorithms refuse to run without `--allow-frontier` or `GIGI_ALLOW_FRONTIER=1`. The gate is in the harness, so the Python API, the CLI and any agent tool inherit it.
- `docs/MATURITY.md` and `docs/GLOSSARY.md`.
- `CHANGELOG.md`, `docs/RELEASING.md`, and a tag-driven release workflow that builds, tests, publishes to PyPI via trusted publishing, and creates a GitHub Release with notes cut from this file.
- `scripts/sync-version.py`, so `uv version` remains the only bump command and `CITATION.cff` follows it.

### Changed
- `gigi.__version__` now comes from the installed package metadata instead of a second hardcoded copy.
- `RunResult` records the gigi version that produced it, so a stored run is attributable to a build.
- The wheel now ships the registry content (`algorithms/`, `datasets/`, `families/`, `people/`); an installed package was previously code with an empty registry.

---

### The original v0.1 core

### Added
- **Registry.** `algorithms/<id>/method.yaml` as the only registration step: provenance and Gigi credits kept as separate attribution layers, a machine-readable `maths:` block with executed invariants and named choice points, typed and mirrored `relationships`, and a `family` that resolves against `families/families.yaml`.
- **Two algorithms.** `pagerank` (stable) and `degree_centrality` (emerging), each on the reference implementation, NetworkX, igraph and rustworkx.
- **Five divergences, all reproduced by CI.** NetworkX's `weight="weight"` default turning PageRank weighted; rustworkx refusing undirected PageRank; rustworkx's degree centrality disagreeing with in+out degree on three fixtures; and a 0 / 1 / NaN three-way split on the single-node graph.
- **Verification harness.** `gigi verify` asks two questions and never mixes them: do backends agree where the registry says they agree, and does every declared divergence still reproduce.
- **Known answers.** `tests/expected.yaml` per algorithm -- expected values derived from the definition, never from running the code -- as the reference implementation's independent check.
- **A priced maturity ladder** in `gigi/requirements.py`; `gigi review` shows what a tier requires and what promotion would take.
- **Nine adversarial fixtures** as reviewable CSV, including `empty` and `single-node`.
- **People registry** and `CITATION.cff`, with every attribution id resolved by the test suite.
- **Surfaces.** A CLI over the same three library functions, a static site (`gigi site build`), a single-JSON export (`gigi export`), and Typst/PDF export (`gigi typst`) with a `--review` mode that puts open questions in the margin.
- **Readability as a checked property**: module and function caps, mandatory docstrings, and a capability budget, all enforced by tests.

### Fixed
- A NaN score compared as equivalent to anything, because `abs(x - NaN) > tolerance` is False. Non-finite scores now never compare as equal.

[Unreleased]: https://github.com/graphgeeks-lab/gigi-algo/compare/v0.1.0...HEAD [0.1.0]: https://github.com/graphgeeks-lab/gigi-algo/releases/tag/v0.1.0
