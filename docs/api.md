# Python API

The Python API and CLI use the same execution path. Load a registry method, load a fixture, run a backend, and verify its claims:

```python
import gigi

method = gigi.method("pagerank")
data = gigi.load_dataset("weighted-small")
result = gigi.run("pagerank", "networkx", data)
report = gigi.verify("pagerank")
```

## Registry and data

```{autofunction} gigi.method
```

```{autofunction} gigi.methods
```

```{autofunction} gigi.load_dataset
```

```{autofunction} gigi.inspect
```

## Execution and evidence

```{autofunction} gigi.run
```

```{autofunction} gigi.compare
```

```{autofunction} gigi.verify
```
