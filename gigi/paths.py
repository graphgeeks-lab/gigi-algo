"""Where the content lives.

Gigi is content-first: the interesting parts are `algorithms/` and `datasets/`,
not the Python package. Both directories are resolved relative to the repository
root, and both can be pointed elsewhere with an environment variable so a
downstream project can keep its own registry.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """The directory holding `algorithms/`, `datasets/`, `families/` and `people/`.

    In a checkout that is the repository root, found by walking up from this
    file. In an installed wheel there is no checkout: the same four directories
    ship inside the package as `gigi/_content/`, and that is returned instead.
    A checkout always wins, so editing the registry in place keeps working.
    """
    here = (start or Path(__file__)).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "algorithms").is_dir():
            return candidate
    packaged = here.parent / "_content"
    if (packaged / "algorithms").is_dir():
        return packaged
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
