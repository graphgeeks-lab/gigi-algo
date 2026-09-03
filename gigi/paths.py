"""Where the content lives.

Gigi is content-first: the interesting parts are `algorithms/` and `datasets/`,
not the Python package. Both directories are resolved relative to the repository
root, and both can be pointed elsewhere with an environment variable so a
downstream project can keep its own registry.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Walk up from this file until we find the directory holding `algorithms/`."""
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "algorithms").is_dir():
            return candidate
    return here.parent.parent


def algorithms_dir() -> Path:
    override = os.environ.get("GIGI_ALGORITHMS_DIR")
    return Path(override).resolve() if override else repo_root() / "algorithms"


def datasets_dir() -> Path:
    override = os.environ.get("GIGI_DATASETS_DIR")
    return Path(override).resolve() if override else repo_root() / "datasets"


def families_file() -> Path:
    override = os.environ.get("GIGI_FAMILIES_FILE")
    return Path(override).resolve() if override else repo_root() / "families" / "families.yaml"


def state_dir() -> Path:
    """Local, gitignored run state. No database in v0.1 on purpose."""
    override = os.environ.get("GIGI_STATE_DIR")
    path = Path(override).resolve() if override else Path.cwd() / ".gigi"
    return path
