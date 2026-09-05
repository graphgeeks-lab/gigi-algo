# 0009 — Known answers, and a priced maturity ladder

**Status:** accepted

## Context

Every backend is verified against the reference implementation. That makes the reference the oracle — and an oracle nobody checks. If `reference.py` is wrong, every cross-backend comparison passes anyway, because they all agree with each other about the wrong answer. The conformance suite cannot see this: it would be checking the code against itself.

Separately, the maturity tiers (`frontier`, `emerging`, `stable`) were defined by prose in several places, and the checks that enforced them were scattered across test files. Three documents held three slightly different opinions about what `stable` required.

## Decision

**Known answers.** Each algorithm carries `tests/expected.yaml`: small graphs, parameters, expected scores, and a `derived` field saying where the expected values came from — symmetry, a closed form, a hand count, a worked example in a paper. Never "I ran the code". A case derived by running the code proves nothing; a case derived from the definition proves the reference implements the definition. Contributors write YAML; the test suite is generated from it.

Inline graphs check the reference alone. Fixture-backed cases also run on every backend, where a declared divergence can excuse exactly the backend and fixture it names.

**One price list.** `gigi/requirements.py` holds every requirement with the lowest tier at which it is mandatory. `gigi review`, `tests/test_requirements.py` and CONTRIBUTING.md all read from it. A requirement not yet mandatory is still checked and reported as what promotion would take.

| tier | owes |
|---|---|
| `frontier` / `historical` | the entry exists: reference, family, people resolve |
| `emerging` | the maths is stated; one invariant runs; two known answers, each derived; divergences credited; notes written |
| `stable` | every divergence has a `detect` block and a choice point; four known answers; provenance cited; runs on `empty` and `single-node`; two backends beyond the reference |

**Degenerate fixtures are first-class.** `empty` and `single-node` are where implementations disagree most and are tested least. On the day they were added they found a three-way split — 0, 1, NaN — on the smallest possible graph.

## Consequences

- The oracle has an independent check, in proportion to how many known answers a contributor is willing to derive. That is the right lever: more effort buys more confidence, and the effort is visible in the file.
- Promotion is a checklist, not a judgment call: `gigi review` prints exactly what an `emerging` entry lacks for `stable`. Whether to promote remains a human decision.
- Raising a requirement raises it everywhere at once, and the test suite tells every entry that no longer qualifies.
- An invariant violation on a fixture named by a declared divergence is an explained difference, not a failure — the same rule that already applied to score differences and errors.
- A NaN score is never equivalent to anything. This was not true before the singleton fixture existed, because `abs(x − NaN) > tolerance` is False.
