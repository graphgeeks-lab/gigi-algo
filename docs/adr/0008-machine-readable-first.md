# 0008 — Machine-readable first

**Status:** accepted

## Context

The readers of this registry will increasingly not be people. An agent choosing
an algorithm, a verifier checking a candidate, a search system proposing a
faster implementation — none of them can read `maths.md`, and none of them
should be asked to infer facts from prose. An LLM that reads "PageRank scores
sum to one" and decides that is probably true has not verified anything.

At the same time, prose is how a person actually learns an algorithm, and
dropping it would make the registry unreadable.

## Decision

Every fact exists in structured form. Prose supplements it and never carries it
alone.

| Fact | Structured home | Prose home |
|---|---|---|
| What it computes | `maths.definition` (statement + LaTeX) | `maths.md` |
| What must be true of the answer | `maths.invariants` — **executed** | `maths.md` |
| Where the definition leaves a choice | `maths.under_determined` | `maths.md` |
| Where engines actually differ | `divergences` — **executed** | `notes.md` |
| What it is like, and how | `relationships` (typed, conditioned) | — |
| What kind of question it answers | `family` → `families/families.yaml` | — |
| Who created it | `provenance` | `attribution_notes` |
| Who built the entry | `gigi:` → `people/people.yaml` | — |

Four rules follow:

1. **Claims are executable, or explicitly marked as not.** `invariants` run on
   every engine and every fixture. `divergences` are reproduced. A property
   with `check: true` whose id names no function in `gigi/invariants.py` fails
   the build. An agent can verify rather than trust.
2. **Ambiguity is a first-class record.** `under_determined` names the choice
   points in the definition, so a reader knows where it must ask rather than
   guess — and so a new engine can be assessed before it is ever run.
3. **Relationships are typed and conditioned.** "See also" tells a machine
   nothing. "Generalises eigenvector centrality, and coincides with it as
   damping approaches 1 on a strongly connected graph" tells it when a
   substitution is legitimate. `equivalent_under` without a condition is
   rejected.
4. **No fact is inferred from prose at runtime.** The one place a language
   model belongs is turning a person's sentence into a typed `ProblemIntent`.
   Everything downstream — filtering, ranking, planning, verification — reads
   the structured fields. This is the anti-hallucination boundary, and it is
   the reason the structure has to be complete enough to decide on.

`gigi export` serialises the whole registry as one JSON document from the same
models the library uses, so an outside consumer sees exactly what `gigi verify`
checks.

## Consequences

- Stating a property costs almost nothing and buys verification everywhere: two
  lines of YAML are asserted across every engine and fixture, forever.
- The registry is a graph — algorithms, families, people, fixtures, findings,
  and typed edges between them. It can be traversed, and eventually analysed
  with Gigi's own algorithms.
- Writing a spec is more work than writing a document. That is the trade: a
  document is cheaper to produce and worth less to everyone downstream.
- The structured and prose forms can disagree, and nothing catches that
  automatically. Review has to. `maths.md` and `maths:` are reviewed together.
