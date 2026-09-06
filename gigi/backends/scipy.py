"""The SciPy adapter.

The first backend that takes something other than a graph, which is the point
of it: the adapter contract was written around `GraphData` and had to be shown
to hold for a second kind of input before anyone believed it would.

Owns three things and no more: whether the library is installed, what version
it is, and how to turn `VectorData` into the dense array SciPy's distance
functions expect.

Method calls live beside the method, in
`methods/<id>/implementations/scipy.py`, so adding a method never means editing
this file.
"""

from __future__ import annotations

from gigi.backends.base import ConvertedVectors, Dataset, require_vectors

NAME = "scipy"


def available() -> bool:
    """Is the library importable in this environment?"""
    try:
        import scipy  # noqa: F401
    except ImportError:
        return False
    return True


def version() -> str | None:
    """The installed version, recorded on every run, or None if absent."""
    try:
        import scipy
    except ImportError:
        return None
    return scipy.__version__


def convert(data: Dataset) -> ConvertedVectors:
    """Build a dense (n, d) array whose row order matches `ids`.

    Row order is the contract: an implementation that keys its output by index
    -- and `pdist` returns a bare condensed vector, so it must -- can only be
    mapped back to ids if this order is stable.
    """
    vectors = require_vectors(NAME, data)

    import numpy as np

    ids = vectors.ids
    rows = vectors.rows()
    matrix = np.array([rows[name] for name in ids], dtype=float)

    return ConvertedVectors(native=matrix, ids=ids, dimensions=vectors.dimensions)
