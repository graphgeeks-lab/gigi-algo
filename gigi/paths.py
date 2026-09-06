"""Where the content lives.

Gigi is content-first: the interesting parts are `methods/` and `datasets/`,
not the Python package. Every content directory is resolved relative to the
repository root, and each can be pointed elsewhere with an environment variable
so a downstream project can keep its own registry.

`CONTENT_DIRECTORIES` is the list of what has to ship in a wheel. It lives here
rather than in `pyproject.toml` alone so the packaging test can check the two
against each other -- a content directory that is added here and forgotten
there produces an installed package that is missing part of the registry, and
nothing else would notice.
"""

from __future__ import annotations

import os
from pathlib import Path


# Every directory of registry content, in the order a reader meets them.
CONTENT_DIRECTORIES = (
    "methods",
    "datasets",
    "problems",
    "families",
    "domains",
    "semantics",
    "people",
)


def repo_root(start: Path | None = None) -> Path:
    """The directory holding `methods/`, `datasets/` and the rest of the content.

    In a checkout that is the repository root, found by walking up from this
    file. In an installed wheel there is no checkout: the same directories ship
    inside the package as `gigi/_content/`, and that is returned instead. A
    checkout always wins, so editing the registry in place keeps working.
    """
    here = (start or Path(__file__)).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "methods").is_dir():
            return candidate
    packaged = here.parent / "_content"
    if (packaged / "methods").is_dir():
        return packaged
    return here.parent.parent


def methods_dir() -> Path:
    """Where method entries live."""
    override = os.environ.get("GIGI_METHODS_DIR")
    return Path(override).resolve() if override else repo_root() / "methods"


def datasets_dir() -> Path:
    """Where fixtures live."""
    override = os.environ.get("GIGI_DATASETS_DIR")
    return Path(override).resolve() if override else repo_root() / "datasets"


def column_meanings_file() -> Path:
    """The column-name hint vocabulary for the semantic check."""
    override = os.environ.get("GIGI_COLUMN_MEANINGS_FILE")
    return (
        Path(override).resolve()
        if override
        else repo_root() / "semantics" / "column_meanings.yaml"
    )


def problems_dir() -> Path:
    """Where problem definitions live."""
    override = os.environ.get("GIGI_PROBLEMS_DIR")
    return Path(override).resolve() if override else repo_root() / "problems"


def domains_file() -> Path:
    """The domain registry."""
    override = os.environ.get("GIGI_DOMAINS_FILE")
    return Path(override).resolve() if override else repo_root() / "domains" / "domains.yaml"


def families_file() -> Path:
    """The family registry."""
    override = os.environ.get("GIGI_FAMILIES_FILE")
    return Path(override).resolve() if override else repo_root() / "families" / "families.yaml"


def state_dir() -> Path:
    """Local, gitignored run state. No database in v0.1 on purpose."""
    override = os.environ.get("GIGI_STATE_DIR")
    path = Path(override).resolve() if override else Path.cwd() / ".gigi"
    return path
