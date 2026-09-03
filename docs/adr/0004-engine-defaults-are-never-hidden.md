# 0004 — Engine defaults are never hidden

**Status:** accepted

## Context

The project exists because engines disagree, and they disagree mostly through
defaults nobody types. NetworkX's `weight="weight"` is the clearest case: it
turns unweighted PageRank into weighted PageRank without a warning.

## Decision

Every `RunResult` records `requested_parameters` and `effective_parameters`
separately. An implementation must report what the engine actually used,
including values the caller never supplied.

Canonical parameters are tri-state where the engines disagree. `weight_property`
is `null` for "use the engine's default", `false` for "explicitly unweighted",
or a column name. `null` is the default precisely so that the divergence is
reachable and testable rather than papered over.

## Consequences

- `gigi run` prints requested and effective parameters side by side.
- Verification pins ambiguous parameters (`verification.parameters` in
  `algorithm.yaml`), so a remaining disagreement is semantic rather than a
  difference of stopping points.
- `RunResult` is already an experiment record minus a `candidate_id`, which is
  what makes the discovery work in the second PRD an addition rather than a
  rewrite.
