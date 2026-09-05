# 0007 — Attribution has layers

**Status:** accepted

## Context

A field like `inventor: Edsger Dijkstra` is convenient and usually wrong. Algorithms have precursors, independent discoveries, later generalisations, and a famous name that is not the whole history. PageRank is a clear case: the 1998 paper names four authors, while the recursive link-ranking idea appears in Katz (1953), Hubbell (1965) and Pinski & Narin (1976), and comparable web ranking work was filed independently around the same time.

Separately, a registry entry is itself work: someone writes the spec, someone writes the reference implementation, someone writes the adapter, someone finds the divergence. Collapsing those into a contributors footer erases the distinctions that make the credit meaningful.

## Decision

Four questions, four answers, never merged:

```
who created the algorithm  !=  who implemented it in Gigi
                           !=  who verified it
                           !=  who found the divergence
```

- `provenance:` in `method.yaml` holds historical attribution — original authors, the original work, structured precursors, and `attribution_notes` for the parts that resist structure. Ambiguity is recorded, not resolved.
- `gigi:` holds contribution to *this repository*, by role, as ids into `people/people.yaml`.
- `discovered_by` sits on the divergence, because finding one is its own contribution and rarely the same person who wrote the adapter.

Every id in `gigi:` and `discovered_by` must resolve, or the test suite fails — attribution is a claim, and claims get checked here.

## Consequences

- Profile pages show lineage, never a score. A points total rewards volume and invites gaming; "wrote the reference implementation for PageRank and found the NetworkX weight divergence" is something a person can put their name to.
- `test_provenance_is_separate_from_credits` fails if a name appears in both layers, which forces the ambiguity into `attribution_notes` where it belongs.
- Historical correction becomes a first-class contribution: fixing a precursor list needs no code.
