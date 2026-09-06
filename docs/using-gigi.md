# Using Gigi

## Start with a question

```console
$ gigi ask "who are the influencers in my network"
```

When a provider is configured, a model can match that ordinary wording to
registry entries. It only selects entry identifiers; the words Gigi prints are
always from the registry. `gigi providers` shows what is configured, and
`gigi ask "..." --model none` forces offline word matching.

## Compare implementations

```console
$ gigi compare pagerank -d weighted-small --defaults
```

This shows the answer each backend gave and the effective parameters it used.
It is how Gigi makes a default such as NetworkX's weighted PageRank visible.

## Check data meaning

```console
$ gigi why pagerank --graph road-distances-small
```

Gigi explains what a method answers, what it does not answer, and how it reads
input columns. A distance column used as PageRank strength is a semantic
mismatch, even though both are numbers.

## Find the evidence

```console
$ gigi show pagerank
$ gigi maths pagerank
$ gigi origin pagerank
$ gigi review pagerank
```

These commands move from the method summary to its definition, historical
provenance, and the remaining questions for a human reviewer.
