# 0013 — `gigi ask` retrieves; it does not generate

**Status:** accepted; landed with the agent surface

## Context

The launch plan called for "Ask Gigi": a natural-language way in, so somebody
with a graph and a question does not have to already know that the thing they
want is called `degree_centrality`.

The obvious build is a retrieval-augmented question answerer — pull the relevant
registry entries, hand them to a model, print the reply. It would demo well.

It would also quietly destroy the only thing this project has. Every claim in
this registry is verified: divergences are re-run by CI, invariants execute on
every backend, known answers are derived by hand rather than observed. A
generated sentence sitting in `gigi ask` output looks exactly like a checked one
and carries none of the guarantee. The first time Gigi confidently describes a
divergence that does not exist, the registry is worth less than a blog post,
because a blog post never claimed to be verified.

The failure mode is not hypothetical or rare. It is the *default* behaviour of a
model handed a retrieval result that came back empty.

## Decision

**`gigi ask` has no model behind it and makes no network call.** It matches the
question against text the registry already carries for exactly this purpose —
`aliases`, `ai_context.synonyms`, a problem's `question` — resolves matches to
the methods that solve them, and prints that. Where the registry is silent, it
says so.

Three outcomes, and the last two are the point:

| | what it prints |
|---|---|
| methods answer it | those methods, with maturity and a `gigi why` pointer |
| the question is known, nothing solves it | *"nothing here answers this"*, and which methods declare it out of scope |
| nothing matches | *"nothing in the registry matches this question"* |

**Weak matches may be shown. They may never answer.** A match must clear both an
absolute floor and a share of the best score before it can drive a
recommendation. Both bars exist because the first version had neither, and it
recommended cosine similarity for "the cheapest route between two cities" (the
word *two* overlapped "how alike are these two things") and connected components
for "how do I find communities" — which the registry *explicitly says* is the
wrong answer. Those are now regression tests.

**Generation is somebody else's job, and Gigi hands them the material.**
`gigi ask --format context` emits the grounded facts with the instruction
attached: answer only from this, cite ids, say so if it does not answer. The MCP
server is the better version — the model calls `gigi_ask`, gets the same
grounding plus a `guidance` field, and can then call `gigi_verify` to check any
claim it is about to make.

That inverts the usual arrangement, and deliberately: the model is the caller,
Gigi is the source, and the boundary between "what the registry says" and "what
the model inferred" stays visible to the user because the two are on opposite
sides of a tool call.

## Consequences

**No provider abstraction was built.** There is no `PROVIDERS` dict, no
`anthropic.py`, no key handling, no `--model` flag. Speculative generality is
the thing this codebase's rules exist to prevent, and an extension point with
nothing behind it is exactly that. If a generating mode is ever wanted, it slots
in where the answer is rendered, and it should arrive with the argument for why
the guarantee above is safe to weaken.

**`aliases:` finally has a reader.** It was declared on every method since v0.1
and consumed by nothing. `search()` is its first consumer, which is a decent
retrospective argument that it was worth carrying — and a test now keeps it
honest.

**Agents can execute, and the maturity gate still holds.** `gigi_run`,
`gigi_compare` and `gigi_verify` do real work, because a registry an agent can
only read is a document and the interesting part is checking claims. `frontier`
methods refuse to run without opt-in, from the harness, exactly as they do for
every other caller — an agent is not a special case, and that is the one place
it would have been tempting to make it one.

**Tool failure and run failure are different things.** `{"error": ...}` means
the tool call failed; a backend that could not run is `status: "error"` with
`status_detail`, and is a *successful* tool call returning a true result. They
were the same field for ten minutes, which made a legitimate result look like a
malfunction to MCP's `isError` flag.

**MCP is hand-rolled, in about sixty lines.** The protocol surface Gigi needs is
four methods and a JSON-RPC envelope. A dependency that saves fifty lines is
still a dependency to install, pin, and have break the wheel. If resources,
prompts, sampling or progress are ever needed, that trade changes and the `mcp`
package is the right answer.

**The agent surface is reporting, not capability**, and the budget counts it
that way — 382 lines that do not tell against the library, because every handler
is a call into `registry`, `ask` or `harness`. The retrieval that genuinely
computes went into `gigi/ask.py` instead. That placement was made before
anything was measured, which is the only reason the classification is a decision
rather than a rationalisation.
