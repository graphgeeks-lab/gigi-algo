# Gigi documentation

Gigi is an executable registry of method semantics. It records what a method
means, runs implementations across backends, and keeps the findings true by
checking them in CI.

The handbook explains how to use and contribute to Gigi. The generated
registry site holds the method pages, provenance, maths, backend evidence, and
verification results for each entry.

```{toctree}
:maxdepth: 2
:caption: Start here

quickstart
using-gigi
api
contributing
```

```{toctree}
:maxdepth: 2
:caption: Concepts and contribution

ARCHITECTURE
GLOSSARY
MATURITY
ONTOLOGY
REVIEWING
RELEASING
CODEBASE
```

```{toctree}
:maxdepth: 1
:caption: Design decisions

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
