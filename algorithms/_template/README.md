# Algorithm template

**This is a working example, not a set of blanks.** It implements degree
centrality end to end — reference implementation, NetworkX adapter, provenance,
credits — so you can run it before you change anything.

```bash
cp -r algorithms/_template algorithms/<your_algorithm_id>
# edit `id:` in algorithm.yaml to match the directory name
gigi run <your_algorithm_id> --graph tiny-directed --engine reference
gigi compare <your_algorithm_id> --graph tiny-directed
gigi verify <your_algorithm_id>
```

All three should work immediately. Now replace the example, one piece at a time:

1. **`algorithm.yaml`** — id, name, problem, parameters, output. Set
   `maturity: emerging` to start.
2. **`provenance:`** — who created the algorithm, the original work, and any
   precursors. Do not reduce this to a single inventor; put contested or messy
   attribution in `attribution_notes`. See
   [ADR 0007](../../docs/adr/0007-attribution-has-layers.md).
3. **`gigi:`** — who is doing the work here. Add yourself to
   `people/people.yaml` first; an id that does not resolve fails the tests.
4. **`implementations/reference.py`** — your algorithm, readable. Get it right
   before it is fast; it is the oracle everything else is compared against.
5. **`implementations/<engine>.py`** — call the engine, and record what it
   actually used in `effective`.
6. **`maths.md`** — the definition, and the places the definition leaves a
   choice open. Those are where engines diverge.
7. **`notes.md`** — what you measured, after running `gigi verify`.

When engines disagree, work out why, then record it as a `divergence` with a
`detect` block so CI reproduces the claim. When they agree, say so in
`notes.md` — verified agreement is a result too.

Then run `pytest`. Every test that applies to your algorithm was generated from
the files you just wrote; you add none.

Directories starting with `_` are skipped by the registry, so this template
never appears in `gigi list`. It is still exercised by `tests/test_template.py`,
which copies it under a real id and runs the whole pipeline — so if the example
breaks, CI says so.
