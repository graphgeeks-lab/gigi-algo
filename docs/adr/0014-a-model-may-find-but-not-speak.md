# 0014 — A model may find, but not speak

**Status:** accepted; amends [ADR 0013](0013-gigi-ask-does-not-generate.md)

## Context

ADR 0013 said `gigi ask` would have no model behind it, and gave a good reason:
a generated sentence in Gigi's output looks exactly like a verified one and
carries none of the guarantee.

It was right about the danger and wrong about the scope. It banned *a model*,
when what needed banning was *a model asserting things*. Those are not the same,
and the difference is the whole of this decision.

The cost of the over-broad rule showed up immediately. Word overlap cannot read
paraphrase:

```console
$ gigi ask "which nodes matter most"
Answered by
  degree_centrality
```

PageRank is missing. Not because the registry does not answer the question — it
does, via `recursive_node_influence` — but because *matter* shares no token with
*important*. A user who phrases their question the ordinary way gets a worse
answer than the registry contains, and has no way to know it.

That is a bad failure. It is silent, it looks like a complete answer, and it
gets worse as the registry grows and the odds of guessing its vocabulary fall.

## Decision

**A model chooses which registry entries a question is about. It writes nothing
a user reads.**

The two jobs, separated:

| | who does it | can it invent something? |
|---|---|---|
| **finding** — which entries is this about? | a model, when configured | no: it picks from a closed catalogue, and every id is validated |
| **saying** — what do those entries mean? | the registry, always | no: every word is content somebody wrote and CI checks |

The safety property is that the answer space is *enumerable and checkable*. The
model receives a catalogue of ids and returns a list of them. `ask.resolve()`
looks up every one and silently drops anything that does not exist. A model
cannot add a method to Gigi by mentioning it — the worst it can do is match
nothing, and matching nothing falls back to word matching.

**Every failure degrades rather than breaking.** No key, no network, a timeout,
prose instead of JSON, every id invented — all of them fall through to the word
matcher. `gigi ask` works offline, and that is not negotiable.

**The path is always visible.** Every answer prints `matched by word matching`
or `matched by anthropic (model)`. A user should not have to guess whether a
model was involved in choosing, or notice for themselves that it quietly fell
back.

**Providers are a dict, not a plugin system** — `anthropic`, `openai`, `ollama`,
the same shape as `backends`. Raw HTTP rather than three SDKs, for the reason
the MCP server is hand-rolled: small stable JSON APIs, and a dependency that
saves forty lines is still one to install, pin, and have break the image.
`OPENAI_BASE_URL` covers vLLM, llama.cpp, LM Studio and gateways; Ollama covers
the case that matters for a private registry, where nothing may leave the
machine.

## What is still refused

ADR 0013 stands on everything else. There is no mode in which a model writes
prose about what a method does, explains a divergence, or summarises the maths.
`gigi ask --format context` and the MCP tools exist so a model *elsewhere* can
do that with grounded material and its own name on the output — the boundary
between "what the registry says" and "what a model inferred" stays visible
because the two sit on opposite sides of a tool call.

The MCP `gigi_ask` tool deliberately does **not** use a provider. Its caller is
already a model and can rephrase its own question; a second model in that loop
would add latency and cost to reach the same place.

## Consequences

**It fixes the case that prompted it**, and there is a test named for it: with a
model, "which nodes matter most" returns degree centrality *and* PageRank.

**Most of the test file is a model behaving badly** — inventing ids, returning
prose, returning `{"methods": [...]}` instead of `{"ids": [...]}`, timing out,
being told to claim Gigi does community detection. In every case the user gets
a true answer or an honest "nothing matches". `pagernak` is dropped rather than
fuzzy-matched to `pagerank`, because guessing at a model's typo is inventing a
match on its behalf.

**The vendors' API shapes are taken on trust, and that is the one unverified
claim here.** The request and response shapes for Anthropic, OpenAI and Ollama
are written from their documentation, not measured against a live endpoint --
there is no key in CI and there should not be. What *is* measured is everything
on this side of the wire: `tests/test_providers.py` runs the real urllib path
against a local HTTP server and checks the URL, the headers, the body shape and
the parse. If a vendor changes its response shape, the failure surfaces as a
`ProviderError` and `gigi ask` falls back to word matching -- degraded, not
broken, which is why this is an acceptable thing not to know.

**`--model auto` is the default**, and that is a judgement worth naming: a
configured API key is a deliberate act, and the alternative — silently doing
worse than the machine is capable of — is a poor default for the one command
aimed at people who do not yet know what to search for. `GIGI_MODEL=none`
disables it everywhere, `--model none` per call, and the transparency line means
it is never a surprise after the fact.

**The capability budget went to 3,000, the fifth raise in five releases.** A
number that only ever goes up measures nothing, so this release also adds the
check that cannot be satisfied by raising it: capability lines *per shipped
method*, which has to fall as the registry grows. It encodes the actual design
claim — adding a method is content, not code — and it gets stricter on its own.
