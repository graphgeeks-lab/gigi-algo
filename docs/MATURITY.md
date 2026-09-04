# Maturity: the four tiers, and how an entry moves

Every algorithm declares one tier. It is not a badge — it decides what CI
demands of the entry, and whether the entry will run at all.

| tier | what it says | what it costs | will it run? |
|---|---|---|---|
| `frontier` | we are not standing behind this | almost nothing: a reference implementation, a family, resolvable people | **only with explicit opt-in** |
| `emerging` | the maths is written down and independently checked | definition, an executed invariant, two derived known answers, credited divergences, real notes | yes |
| `stable` | every claim is testable, and has been tested | all of the above, plus testable divergences tied to choice points, four known answers, cited provenance, degenerate fixtures, two engines beyond the reference | yes |
| `historical` | frozen; kept for the record | same low bar as `frontier` | yes, but never recommended |

The exact list lives in [`gigi/requirements.py`](../gigi/requirements.py) and
nowhere else, so this table cannot drift away from what is enforced. Run
`gigi review <algorithm>` to see where an entry actually stands.

---

## Moving from `emerging` to `stable`

### 1. Ask what is missing

```bash
gigi review degree_centrality
```

The review ends with either a list headed **"To reach `stable`"** or the line
**"Meets every requirement of `stable` — ready to promote"**. Each unmet item
names the requirement and the specific gap, so the list is a to-do, not a
verdict.

What `stable` adds over `emerging`, and why:

- **Every divergence has a `detect:` block.** An untestable claim rots. A
  `stable` entry's divergences are re-run on every build.
- **Every divergence is tied to a choice point** in `maths.under_determined`.
  Engines do not differ at random; if they differ, the definition left room,
  and the entry should say where.
- **Four known answers, not two.** More independent checks on the oracle.
- **Original authors and work cited.** A stable entry is one people will cite.
- **It runs on `empty` and `single-node`.** The degenerate cases most
  implementations are never tested on — where the 0/1/NaN split was found.
- **Two engines besides the reference.** Cross-engine evidence needs a cross.

### 2. Promote

```bash
gigi promote degree_centrality --dry-run   # check, change nothing
gigi promote degree_centrality             # check, then edit algorithm.yaml
```

`promote` re-runs every requirement of the target tier and **refuses** if any
is unmet. It only ever moves up the ladder; demoting is a deliberate hand edit,
not a command.

Passing the checks is *necessary, not sufficient*. The command exists so the
decision is made on top of the checks rather than instead of them, and it
finishes by naming the three things it cannot do for you:

- write the CHANGELOG line saying what the promotion means for a user;
- get someone who did not write the entry to read it
  ([docs/REVIEWING.md](REVIEWING.md));
- commit the change.

### 3. The rule about who promotes

An entry is not promoted by the person who wrote it, alone. This matters more
later than it does now: once candidates can be machine-generated, a search
process that can promote its own output has no verifier at all. The rule is
cheap to keep from the start, and expensive to introduce afterwards.

---

## Using `frontier`

`frontier` is for work you want in the registry but do not yet vouch for: an
implementation of a recent paper, a variant you are exploring, an engine
adapter whose semantics you have not pinned down, or — later — a
machine-generated candidate.

### It will not run by accident

```console
$ gigi run my_variant --graph tiny-directed
FrontierBlocked: my_variant is `frontier`: not verified, not stood behind, and
never run by accident. Opt in explicitly with --allow-frontier, or set
GIGI_ALLOW_FRONTIER=1 for a session.
```

Opt in when you mean it:

```bash
gigi run my_variant --graph tiny-directed --allow-frontier
gigi compare my_variant --graph tiny-directed --allow-frontier
gigi verify my_variant --allow-frontier

GIGI_ALLOW_FRONTIER=1 gigi verify          # a whole session
```

```python
gigi.run("my_variant", engine="reference", graph=graph, allow_frontier=True)
```

The gate is in the harness, not the CLI, so **every** caller inherits it — the
Python API, the CLI, and any agent tool built on them. An agent asking for "the
best centrality algorithm" can never be handed a frontier one silently; it has
to ask for it by name and opt in. That is the whole reason the tier exists.

### What it costs, and what it does not

A frontier entry still needs a reference implementation, a resolvable family
and resolvable people. It does **not** need known answers, testable
divergences, cited provenance, or the degenerate fixtures. That is the point:
the bar is low so that unfinished work has somewhere honest to live, and the
gate is what makes a low bar safe.

Consequently:

- `gigi verify` (no argument) **skips** frontier entries with a visible `SKIP`
  line rather than failing or pretending.
- `gigi verify <a-frontier-entry>` **fails** unless you opt in — asking for one
  by name and not being allowed to have it is an error, not a skip.
- `gigi site build` publishes the entry with **no verification evidence**,
  which is the honest thing to show.
- `gigi review` works normally: reviewing a frontier entry is exactly how you
  decide whether it should stop being one.

### Adding one

Identical to any other algorithm ([CONTRIBUTING.md](../CONTRIBUTING.md)) except
that you write `maturity: frontier` and stop as soon as it runs. Then use
`gigi review` to see what `emerging` would take.

---

## `historical`

For an algorithm that is superseded but worth keeping: the entry stays, the
tests keep running, and nothing recommends it. Set it by hand — there is no
command, because freezing something is a decision that deserves a commit
message explaining itself.

## Versions

Every run records the gigi version that produced it (`RunResult.gigi_version`),
and every verification report carries it too. `gigi version` shows the build,
the engine versions, and — the part that catches real mistakes — **which
registry is being read**:

```console
$ gigi version
gigi-algo 0.1.0
Python 3.12.3 on win32

registry  /home/you/gigi-algo
          a checkout
          2 algorithms, 9 datasets, 16 families, 1 people, 5 divergences
```

An installed wheel carries its own copy of the registry, so that line tells you
whether you are looking at your working tree or at the packaged content. `gigi
version --json` gives the same thing for scripts.
