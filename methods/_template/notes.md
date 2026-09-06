# Degree Centrality — backend notes

*(Worked example. Write your own version of this file **after** running `gigi verify <your_algorithm>`, and report what you measured rather than what the documentation claims.)*

## Divergences

For each entry in `method.yaml`, explain in plain language what a user should do about it, and include the numbers.

None recorded here: on `tiny-directed`, the reference implementation and `nx.degree_centrality` agree exactly. That is a result, not an absence of one — see below.

## Where the backends agree

Verified agreement is worth writing down. Say which fixture proved it and to what tolerance, so the next person does not re-derive it.

- **Total degree on directed graphs** (`tiny-directed`): NetworkX uses in-degree plus out-degree, matching the reference implementation exactly. Scores: `a` 1.5, `b` 1.0, `c` 1.5.

## Backend quirks worth knowing

`nx.degree_centrality` takes no options. It always normalises, so when a caller asks for `normalized: false` the adapter has to multiply the result back by `n - 1` — and it records `rescaled_by_gigi: true` in its effective parameters rather than quietly returning a number that did not come from the backend.

## Not yet investigated

Be explicit about the gaps. This is usually the best list of contributions to make next.

- Self-loop handling across backends (`self-loop-small` is not yet in `datasets:` for this algorithm).
- igraph and rustworkx adapters.
- In-degree-only and out-degree-only variants, which may deserve to be separate algorithm entries rather than a parameter.
