# 0005 — Divergence claims must be executable

**Status:** accepted

## Context

A registry of engine differences is only worth reading if it is true, and prose
rots silently as engines release new versions. A wrong registry is worse than no
registry.

## Decision

Every divergence in a `stable` algorithm carries a `detect` block naming a
dataset, two engines, the parameters, and the expected outcome (`differ`,
`match` or `error`). CI runs it.

Two independent checks follow, and they are kept separate:

1. **Agreement.** With ambiguous parameters pinned, engines must match the
   reference. A difference that no declared divergence accounts for fails the
   build.
2. **Reproduction.** Every declared divergence must still happen. A divergence
   that stopped happening is stale documentation, and also fails the build.

## Consequences

- The registry cannot drift away from reality without CI noticing.
- An engine upgrade that changes semantics surfaces as a failing check, which is
  the version-drift mechanism the PRD asks for, obtained for free.
- Writing a divergence entry costs more than writing prose. That is intentional.
