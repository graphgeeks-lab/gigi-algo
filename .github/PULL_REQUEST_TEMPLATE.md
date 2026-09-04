## What this changes

<!-- One or two sentences. If you found a divergence, put the numbers here —
     that is the interesting part. -->

## For the reviewer

<!-- Paste the output of `gigi review <algorithm>` if this adds or changes an
     algorithm. It tells the reviewer what they do NOT have to check by hand. -->

```
$ gigi review <algorithm>
```

### The by-eye items

Nothing automated covers these. Say what you did about each, or delete the ones
that do not apply. See [docs/REVIEWING.md](../docs/REVIEWING.md).

- [ ] The reference implementation computes what `maths.definition` says.
- [ ] Someone could learn the algorithm from the reference implementation.
- [ ] `maths.md` and the `maths:` block agree.
- [ ] Each divergence is the backend's behaviour, explained in `notes.md`, and
      not something our adapter caused.
- [ ] The provenance is honest: precursors real, contested credit noted rather
      than resolved in our favour.
- [ ] The `family:` question is one this algorithm actually answers.

## Checks

- [ ] `pytest` passes
- [ ] I added myself to `people/people.yaml` if this credits me
- [ ] I did not add an abstraction with only one implementation

<!-- Adding an algorithm should not require editing anything in gigi/. If it
     did, say why — that is usually a gap worth fixing in the harness. -->
