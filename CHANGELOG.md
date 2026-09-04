# Changelog

Every release has a section here, and the release workflow refuses to publish
a version this file does not describe. The section for a version becomes its
GitHub Release notes, verbatim, so write it for someone deciding whether to
upgrade -- what changed, what it means for them, what they need to do.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

### Added
- `gigi version`, showing the build, the engine versions and **which registry**
  is being read -- a checkout or the copy packaged in the wheel.
- `gigi promote`, which re-checks every requirement of the target tier and
  refuses one that has not been earned. It only moves up the ladder.
- The `frontier` tier is now enforced, not labelled: those algorithms refuse to
  run without `--allow-frontier` or `GIGI_ALLOW_FRONTIER=1`. The gate is in the
  harness, so the Python API, the CLI and any agent tool inherit it.
- `docs/MATURITY.md` and `docs/GLOSSARY.md`.
- `CHANGELOG.md`, `docs/RELEASING.md`, and a tag-driven release workflow that
  builds, tests, publishes to PyPI via trusted publishing, and creates a GitHub
  Release with notes cut from this file.
- `scripts/sync-version.py`, so `uv version` remains the only bump command and
  `CITATION.cff` follows it.

### Changed
- `gigi.__version__` now comes from the installed package metadata instead of
  a second hardcoded copy.
- `RunResult` records the gigi version that produced it, so a stored run is
  attributable to a build.
- The wheel now ships the registry content (`algorithms/`, `datasets/`,
  `families/`, `people/`); an installed package was previously code with an
  empty registry.

## [0.1.0] - 2026-09-03

The first version that proves the thesis: the same named algorithm gives
different answers on different engines, and a registry can show that with
reproducible evidence.

### Added
- **Registry.** `algorithms/<id>/algorithm.yaml` as the only registration step:
  provenance and Gigi credits kept as separate attribution layers, a
  machine-readable `maths:` block with executed invariants and named choice
  points, typed and mirrored `relationships`, and a `family` that resolves
  against `families/families.yaml`.
- **Two algorithms.** `pagerank` (stable) and `degree_centrality` (emerging),
  each on the reference implementation, NetworkX, igraph and rustworkx.
- **Five divergences, all reproduced by CI.** NetworkX's `weight="weight"`
  default turning PageRank weighted; rustworkx refusing undirected PageRank;
  rustworkx's degree centrality disagreeing with in+out degree on three
  fixtures; and a 0 / 1 / NaN three-way split on the single-node graph.
- **Verification harness.** `gigi verify` asks two questions and never mixes
  them: do engines agree where the registry says they agree, and does every
  declared divergence still reproduce.
- **Known answers.** `tests/expected.yaml` per algorithm -- expected values
  derived from the definition, never from running the code -- as the reference
  implementation's independent check.
- **A priced maturity ladder** in `gigi/requirements.py`; `gigi review` shows
  what a tier requires and what promotion would take.
- **Nine adversarial fixtures** as reviewable CSV, including `empty` and
  `single-node`.
- **People registry** and `CITATION.cff`, with every attribution id resolved by
  the test suite.
- **Surfaces.** A CLI over the same three library functions, a static site
  (`gigi site build`), a single-JSON export (`gigi export`), and Typst/PDF
  export (`gigi typst`) with a `--review` mode that puts open questions in the
  margin.
- **Readability as a checked property**: module and function caps, mandatory
  docstrings, and a capability budget, all enforced by tests.

### Fixed
- A NaN score compared as equivalent to anything, because `abs(x - NaN) >
  tolerance` is False. Non-finite scores now never compare as equal.

[Unreleased]: https://github.com/graphgeeks-lab/gigi-algo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/graphgeeks-lab/gigi-algo/releases/tag/v0.1.0
