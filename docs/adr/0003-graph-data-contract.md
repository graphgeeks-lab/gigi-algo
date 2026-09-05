# 0003 — The graph data contract

**Status:** accepted

## Context

Loaders make silent decisions — dropping bad rows, collapsing duplicates, coercing identifiers — and those decisions change results while looking like plumbing.

## Decision

Frozen for v0.1:

| Case | Behaviour |
|---|---|
| Null or empty `source`/`target` | Reject the dataset. Never drop the row. |
| Duplicate edges | Preserve. Multiplicity is data. |
| Self loops | Preserve. |
| Directedness | Read from `graph.yaml`. Never inferred. |
| Weights | Explicit column name in `graph.yaml`. Never guessed. |
| Node identifiers | Canonicalised to strings. |
| Isolated nodes | Only exist if `nodes.csv` declares them. |
| Declared counts | `expected.nodes` / `expected.edges` are checked on load. |

## Consequences

- A malformed fixture fails loudly at load rather than quietly at analysis time.
- String identifiers mean backends that key on integers versus strings do not register as a divergence, which would be noise rather than signal.
- Preserving duplicates makes multigraph handling a testable question, which is how `duplicate-edge-small` earns its place.
