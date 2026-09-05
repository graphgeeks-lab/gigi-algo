# 0010 — General schema, narrow content

**Status:** accepted; the schema half landed in PR 1, content sequenced in PLAN.md

## Context

Gigi is an executable registry of *graph algorithm* semantics. Everything it does well — layered provenance, executed invariants, named choice points, reproduced divergences, a priced maturity ladder — is about a *method*, not about a graph. None of it is graph-specific except the parts we happened to name that way: `AlgorithmSpec`, `requirements` (directed/weighted), `engines`, `algorithms/`.

The adjacent domains are close and real: similarity measures (cosine, Jaro-Winkler), entity resolution (Fellegi-Sunter, blocking), geospatial (spatial indexes, CRS-sensitive distance). A record-linkage pipeline is a graph problem, a similarity problem and a statistical-modelling problem in the same breath, and the semantic mistakes are the same shape in all of them.

The decision is not *whether* to generalise but *when*. Two facts settle it:

- Renaming `AlgorithmSpec` → `MethodSpec` and `algorithms/` → `methods/` after a PyPI release is a breaking change for every consumer and every contributor's muscle memory. Before the first release it costs a day.
- With two entries in the registry, migrating content is trivial. With forty it is a project.

## Decision

Generalise the schema now; keep the content graph-only for the v0.1 release.

**Public positioning is unchanged:** "an executable registry of graph algorithm semantics". The internal architecture is "the knowledge and verification layer for algorithms and computational methods". Those two sentences are allowed to differ, and the second is not marketed until content backs it up.

Specifically:

| now | becomes |
|---|---|
| `AlgorithmSpec` | `MethodSpec` with a `kind` |
| `requirements` (directed/weighted/…) | `inputs`, a discriminated union on `kind` |
| `engines` / `EngineAdapter` | `backends` / `BackendAdapter` |
| `algorithms/` | `methods/`, flat, with `domain` grouping for display only |
| `family: str` (free) | resolves to a family that belongs to a domain |

Added: `DomainSpec`, `ProblemSpec`, structured `UseCaseSpec`, `SemanticInterpretation`, `semantic_role` on parameters, `needs_operations`, and a knowledge-graph compiler.

Two departures from the generalisation spec, both to prevent the registry contradicting itself:

1. **`domain` is derived from `family`, not stored on the method.** The spec puts both on `MethodSpec` *and* has `Family BELONGS_TO Domain`. Two paths to one fact is a drift waiting to happen; there is one path.
2. **Derivable relationships are not authored.** `introduced_by`, `implemented_by`, `verified_by` and `used_in` follow from `provenance`, `backends`, `verification` and `use_cases`. They are knowledge-graph edges, not entries in the hand-written vocabulary — as that spec's own rule says.

## Consequences

- **Every extension point has a price.** A new output kind requires a comparator; a new input kind requires a loader and a profiler; a new invariant requires a check. An enum value that buys nothing executable is rejected. This is what stops a general schema becoming a shape that fits everything and helps with nothing.
- **A graph contributor writes slightly more YAML.** `inputs: [{kind: graph, …}]` is more verbose than `requirements:`. The template absorbs it, and the discriminated union means graph authors never see a similarity field.
- **The acceptance test is four entries, not one.** PageRank, cosine similarity, Fellegi-Sunter and CSR must share one schema without domain-specific hacks leaking sideways. If they cannot, the ontology is wrong and gets fixed before any content is added.
- **`ai_context` and the datatype enum are borrowed from Apache OSSIE**, by copy rather than dependency. OSSIE describes what data means; Gigi describes what a method means; the semantic conflict check needs both halves, and reaching for our own vocabulary where a standard exists would be the wrong instinct. Vendoring keeps their release cadence out of our build.
- **Data structures become a second root**, not a `MethodKind`. See [docs/ONTOLOGY.md](../ONTOLOGY.md); the short version is that our `complexity` field currently asserts `O(k(V+E))` while silently assuming O(1) adjacency, and the structure layer is what makes that claim honest.
