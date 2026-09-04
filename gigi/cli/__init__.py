"""The command line, a thin shell over the Python API.

Commands are split by the question they answer:

    knowledge.py   what do we know?          list, show, review, maths,
                                             families, origin, people, export
    explain.py     what does it mean for me? why, alternatives, related,
                                             problems
    execution.py   what happened when we
                   ran it?                   run, compare, verify, inspect, site

Importing this module registers both sets onto `app`. The entry point in
pyproject.toml is `gigi.cli:app`.
"""

from __future__ import annotations

from gigi.cli.app import app

# Importing for the decorator side effects: each module registers its commands.
from gigi.cli import execution, explain, knowledge  # noqa: E402,F401  (order matters)

__all__ = ["app"]
