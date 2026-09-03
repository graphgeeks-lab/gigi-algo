# Reviewing a contribution

The point of this document is to make review **short and confident**. If you
find yourself checking something a machine could have checked, that is a bug in
our tooling — open an issue.

Start here:

```bash
gigi review <algorithm>
```

It prints three lists, and the split between them is the whole idea.

## 1. Settled by machine — skip these

`gigi review` runs the checks and shows what passed. If it is green, you do not
need to verify by hand that:

- the spec validates, the family resolves, every credited person exists;
- every checkable invariant names a real check, and holds on every engine and
  every fixture;
- the engines agree wherever the registry says they agree, and every declared
  divergence still reproduces;
- relationships are mirrored on the other algorithm;
- the required files exist and every declared engine has an implementation.

That is a lot of correctness you get for free. Spend your attention elsewhere.

## 2. Gaps — usually not blockers

Absences the tool noticed: an engine with no implementation, a fixture the
algorithm is not run against, a choice point nothing tests, a divergence
crediting nobody. Most of these are fine in a first contribution and make good
follow-up issues. Ask about them; do not block on them unless the gap
undermines the entry.

## 3. By eye — this is your job

Short on purpose. A checklist nobody finishes protects nothing.

### Does the reference implementation compute what the definition says?

**The one that matters most.** The reference is the oracle every engine is
compared against, so if it is wrong, every green check above is meaningless.
Nothing automated can check this.

Read `maths.definition` and `implementations/reference.py` side by side —
`gigi review` prints the definition at the end for exactly this. They should
correspond line for line. If you cannot follow the correspondence, that is a
finding, not a failure of your attention.

### Could someone learn the algorithm from the reference implementation?

It is a teaching artifact as much as an oracle ([ADR
0002](adr/0002-reference-optimises-readability.md)). Ask:

- Is there a clever trick that saves time and costs clarity? Reject it — this
  file is never a benchmark target.
- Does a comment explain a line that could have been written more plainly
  instead?
- Would a reader who knows the maths but not this codebase follow it?

### Do `maths.md` and the `maths:` block say the same thing?

**The one seam in the design that nothing verifies.** The prose and the
structured block can drift apart silently, and only review catches it. Read
them together, always.

### Is each divergence the engine's behaviour, and not our bug?

A divergence entry is a public claim that a library does something surprising.
Before accepting one:

- Does `notes.md` explain *why* the engine behaves that way? "NetworkX defaults
  to `weight='weight'`" is an explanation; "NetworkX is wrong" is not.
- Could our adapter be causing it? Check `implementations/<engine>.py` for a
  parameter we passed that we should not have.
- Does the `detect` block reproduce the *claim*, or something adjacent?

### Is the attribution honest?

Check `provenance` against the cited work. Precursors should be real and
relevant; contested credit belongs in `attribution_notes` rather than being
resolved silently. And the two layers must stay apart: an original author is a
historical fact, a Gigi contributor is a person in `people.yaml`. See [ADR
0007](adr/0007-attribution-has-layers.md).

### Is the family right?

A family is a question, not a label. `gigi family <id>` prints the question. If
the algorithm does not answer it, the family is wrong even when the name sounds
right.

## Reviewing a dataset

Fixtures are CSV so you can read the diff. Ask one question: **what does this
fixture settle that no existing one does?** The `description` should answer it.
"Directed graph with two sink nodes, because rank held by a node with no
outgoing edges has to go somewhere" is a reason; "test graph 3" is not.

Counts and feature flags are checked on load, so you do not need to verify
those by hand.

## Reviewing a change to `gigi/`

Rarer, and the bar is higher — this is shared machinery.

- **Which existing thing does this replace?** If the answer is "nothing yet",
  it is probably too early. No abstraction with one implementation.
- Does it keep the dependency direction in
  [docs/CODEBASE.md](CODEBASE.md)? Nothing should import back up that diagram.
- If it grows capability past its budget, the pull request should say what
  bought it. `tests/test_readability.py` will fail otherwise.
- Does the CLI command it adds contain logic? If so, that logic belongs in the
  library, where it can be tested and reused by the Python API and any future
  agent tool.

## What to say in the review

Be concrete about the by-eye items. "Checked the reference against the
definition; the dangling-mass term matches, and I followed the weighted case"
tells the next reviewer what has already been established. "LGTM" does not.
