# Quickstart

Install the release with every supported backend:

```bash
pip install "gigi-algo[all]"
```

Ask a plain-language question, then inspect the method Gigi found:

```console
$ gigi ask "what is PageRank useful for?"
$ gigi why pagerank
$ gigi verify pagerank
```

`gigi verify` checks two things. Implementations must agree whenever Gigi says they should, and each documented divergence must still reproduce. A green result means the evidence was re-run in this installation.

For a source checkout:

```bash
git clone https://github.com/graphgeeks-lab/gigi-algo
cd gigi-algo
pip install -e ".[dev]"
pytest -q
```
