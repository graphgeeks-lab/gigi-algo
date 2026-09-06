"""The scikit-learn adapter.

Same input as the SciPy adapter and the same conversion, which is deliberate:
two backends that agree on the data and disagree on the answer are the only
kind of evidence Gigi collects. If they diverge, it is the definition doing it,
not the array.

Method calls live beside the method, in
`methods/<id>/implementations/sklearn.py`.
"""

from __future__ import annotations

from gigi.backends.base import ConvertedVectors, Dataset, require_vectors

NAME = "sklearn"


def available() -> bool:
    """Is the library importable in this environment?"""
    try:
        import sklearn  # noqa: F401
    except ImportError:
        return False
    return True


def version() -> str | None:
    """The installed version, recorded on every run, or None if absent."""
    try:
        import sklearn
    except ImportError:
        return None
    return sklearn.__version__


def convert(data: Dataset) -> ConvertedVectors:
    """Build a dense (n, d) array whose row order matches `ids`."""
    vectors = require_vectors(NAME, data)

    import numpy as np

    ids = vectors.ids
    rows = vectors.rows()
    matrix = np.array([rows[name] for name in ids], dtype=float)

    return ConvertedVectors(native=matrix, ids=ids, dimensions=vectors.dimensions)
