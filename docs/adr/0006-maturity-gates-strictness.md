# 0006 — Maturity gates strictness, from day one

**Status:** accepted

## Context

The second PRD needs a promotion pipeline for machine-generated candidates. That
is a long way off, but the tier it promotes *through* costs almost nothing to
introduce now, and retrofitting it later would touch every spec.

## Decision

Every `MethodSpec` carries `maturity`: `stable`, `emerging`, `frontier` or
`historical`. In v0.1 it does one job: `stable` algorithms must make their
divergence claims testable, `emerging` ones need not.

## Consequences

- One enum and one branch in the test suite today.
- The same field later gates agent selection (an agent must never silently pick
  a `frontier` implementation) and candidate promotion.
- New algorithms start at `emerging` and are promoted deliberately.
