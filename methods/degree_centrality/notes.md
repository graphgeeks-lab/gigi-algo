# Degree Centrality — backend notes

Everything below was measured by `gigi verify degree_centrality`, not read from documentation.

## rustworkx disagrees, and we cannot say why

`rx.degree_centrality` returns values inconsistent with the node's own `in_degree` plus `out_degree`, as reported by rustworkx itself, on three of our seven fixtures. The reference implementation, NetworkX and igraph all agree with each other and with in+out.

| fixture | node | reference / networkx / igraph | rustworkx |
|---|---|---|---|
| `weighted-small` | c | 2.0 | **1.0** |
| `self-loop-small` | c | 2.0 | **1.0** |
| `duplicate-edge-small` | a | 2.0 | **1.0** |

In each case the affected node is the top-ranked one under the other three backends, so the disagreement changes the answer rather than the sixth decimal place.

**We could not derive the rule.** The obvious hypotheses are each contradicted by a case that agrees:

- *It counts distinct neighbours rather than incidences.* Contradicted by `a→b, a→b` alone, where rustworkx returns 2 (incidences), not 1.
- *It drops self loops.* Contradicted by `a→a, a→b, b→c`, where rustworkx matches the others exactly.
- *It collapses parallel edges.* Contradicted by `a→b` three times, where rustworkx returns 3.
- *It caps the normalised score at 1.* Contradicted by `tiny-directed`, where rustworkx returns 1.5.

What the failing cases have in common is a node with in+out degree of 4 in a three-node graph, where rustworkx returns exactly 2. What the passing cases have in common is nothing that distinguishes them under any rule we tried.

This was reproduced against rustworkx directly, with no Gigi code in the path, so it is not our adapter. It is recorded as category `bug` rather than `semantic` for that reason — but the registry entry states the observation and not a mechanism, because we do not have one.

**Next step:** report upstream with the minimal reproduction above. Until then, `mode: all` on a rustworkx multigraph with reciprocal edges should be cross-checked against another backend.

Tested with rustworkx 0.18.1.

## One node, three answers

`single-node` -- one node, no edges -- is the smallest graph there is, and the backends cannot agree on it:

| backend | score of the only node |
|---|---|
| reference | 0.0 (raw degree; the normaliser n - 1 is zero, so it is not applied) |
| igraph | 0.0 (returns raw counts; Gigi skips the division) |
| **networkx** | **1.0** by convention -- a lone node is maximally central |
| **rustworkx** | **NaN** -- divides 0 by 0 without a guard |

The definition is silent at n = 1, so every implementation has to invent an answer. NetworkX's is defensible and documented, and is recorded as a `semantic` divergence of severity low. rustworkx's is a bug -- NaN propagates into anything downstream -- and it is the case Gigi's `scores_finite` invariant exists to catch. It did, on the day the fixture was added.

Recorded as `networkx-singleton-is-central` and `rustworkx-singleton-nan`, both reproduced by CI.

## Three backends, three normalisation conventions

Nobody diverges here, because Gigi pins it — but it is worth knowing what each backend does when you call it yourself:

| backend | normalises? | can you turn it off? |
|---|---|---|
| NetworkX | always | no — `degree_centrality` takes no options |
| rustworkx | always | no |
| igraph | never | not applicable; `degree()` returns raw counts |
| reference | when asked | yes, `normalized: false` |

So `nx.degree_centrality(G)` and `g.degree()` return numbers that differ by a factor of `n - 1`, and neither function's name warns you. The adapters record which side applied the scaling: NetworkX and rustworkx report `rescaled_by_gigi` when normalisation had to be undone, and igraph reports `normalized_by_gigi` when it had to be applied.

The same split shows up in the directed modes. NetworkX and rustworkx expose three separate functions (`degree_centrality`, `in_degree_centrality`, `out_degree_centrality`); igraph takes a `mode` argument. Gigi's canonical `mode` parameter maps onto both shapes.

## Where the backends agree

Verified, not assumed:

- **Directed degree** (`tiny-directed`, `dangling-small`): all four backends use in-degree plus out-degree by default, agreeing exactly.
- **Isolated nodes** (`disconnected-small`): all four score `n6` at 0.0 and none omits it from the result. The `scores_unique_per_node` invariant exists to catch exactly that omission.
- **Undirected graphs** (`undirected-small`): all four agree, including rustworkx — the disagreement above is directed-only in our fixtures.
- **Weights** (`weighted-small`): all four ignore the `weight` column, as they should. Note this is the *opposite* of PageRank, where NetworkX picks weights up by default — see `networkx-weight-default` in that entry. Same library, same graph, opposite convention, depending on which function you call.

## Not yet investigated

- Whether `mode: in` and `mode: out` diverge anywhere; only `all` is verified, because that is what `verification.parameters` pins.
- Weighted degree (strength), which should be its own algorithm entry.
