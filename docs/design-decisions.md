# Design decisions

These short records explain why Gigi is shaped the way it is. They are
reference material, not a required reading path: start with the handbook and
open a decision when you need the reasoning behind a boundary or trade-off.

<details>
<summary><strong>Data and reference implementations</strong></summary>

- [Arrow in memory, CSV on disk](adr/0001-arrow-in-memory-csv-on-disk.md)
- [Reference implementations optimise for readability](adr/0002-reference-optimises-readability.md)
- [The graph data contract](adr/0003-graph-data-contract.md)

</details>

```{toctree}
:hidden:

adr/0001-arrow-in-memory-csv-on-disk
adr/0002-reference-optimises-readability
adr/0003-graph-data-contract
adr/0004-backend-defaults-are-never-hidden
adr/0005-divergence-claims-must-be-executable
adr/0006-maturity-gates-strictness
adr/0007-attribution-has-layers
adr/0008-machine-readable-first
adr/0009-known-answers-and-the-ladder
adr/0010-general-schema-narrow-content
adr/0011-a-dataset-declares-its-kind
adr/0012-a-result-is-not-always-a-number
adr/0013-gigi-ask-does-not-generate
adr/0014-a-model-may-find-but-not-speak
```

<details>
<summary><strong>Evidence and trust</strong></summary>

- [Backend defaults are never hidden](adr/0004-backend-defaults-are-never-hidden.md)
- [Divergence claims must be executable](adr/0005-divergence-claims-must-be-executable.md)
- [Maturity gates strictness, from day one](adr/0006-maturity-gates-strictness.md)
- [Known answers, and a priced maturity ladder](adr/0009-known-answers-and-the-ladder.md)

</details>

<details>
<summary><strong>Knowledge and stewardship</strong></summary>

- [Attribution has layers](adr/0007-attribution-has-layers.md)
- [Machine-readable first](adr/0008-machine-readable-first.md)
- [General schema, narrow content](adr/0010-general-schema-narrow-content.md)

</details>

<details>
<summary><strong>Extending Gigi carefully</strong></summary>

- [A dataset declares its kind, and a backend says what it takes](adr/0011-a-dataset-declares-its-kind.md)
- [A result is not always a number per key](adr/0012-a-result-is-not-always-a-number.md)
- [`gigi ask` retrieves; it does not generate](adr/0013-gigi-ask-does-not-generate.md)
- [A model may find, but not speak](adr/0014-a-model-may-find-but-not-speak.md)

</details>
