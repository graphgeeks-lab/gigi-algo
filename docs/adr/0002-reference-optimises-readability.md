# 0002 — Reference implementations optimise for readability

**Status:** accepted

## Context

Every algorithm has two kinds of implementation in this repository: a reference
one, and one call per backend. They are pulled in opposite directions — the
reference is both the correctness oracle and the teaching artifact.

## Decision

Reference implementations use no backend library, no vectorisation and no
cleverness. They correspond line by line to `maths.md` where possible. They are
never a benchmark target, and performance is never a reason to change one.

Backend implementations do the opposite: they call the backend and do nothing
else. If a loop over nodes appears in `implementations/<backend>.py`, the code is
in the wrong file.

## Consequences

- The reference converges tightly (`tolerance: 1e-12`) so it is not itself the
  source of numerical noise.
- Reading `reference.py` is a legitimate way to learn the algorithm.
- Reference performance is irrelevant, and benchmarks must exclude it.
