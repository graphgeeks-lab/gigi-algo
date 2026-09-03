# 0001 — Arrow in memory, CSV on disk

**Status:** accepted

## Context

The PRD specifies Apache Arrow / Parquet as the neutral data layer. Arrow is the
right in-memory choice: it is engine-neutral, cheap to convert from, and lets us
measure conversion cost per engine. Parquet on disk is a worse fit for the
fixtures we actually have, because a maintainer reviewing a pull request cannot
see what changed inside a binary file.

## Decision

`GraphData` holds `pyarrow.Table`s. Small fixtures are authored as CSV and read
through `pyarrow.csv`. The loader accepts `edges.parquet` identically, and
fixtures large enough that nobody would read the diff anyway should use it.

## Consequences

- Dataset changes are reviewable line by line.
- Contributors can add a fixture with a text editor.
- We keep the Arrow boundary, so the future Arboris work is unaffected.
- Very large fixtures will need Parquet plus a checksum in `graph.yaml`; that is
  a later addition, not a redesign.
