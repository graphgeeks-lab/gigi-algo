"""An installed wheel is a complete registry, not just the code.

The build smoke in the release workflow proves this against a real wheel.
These are the cheaper, every-push versions of the same concern.
"""

from __future__ import annotations

import tomllib

from gigi.paths import CONTENT_DIRECTORIES, repo_root

# Derived, not restated. A content directory added to gigi/paths.py and
# forgotten in pyproject.toml ships a wheel with half a registry in it, and
# this is the only thing that would notice.
CONTENT = CONTENT_DIRECTORIES


def test_checkout_wins_over_packaged_content(tmp_path):
    """In a checkout, walking up finds the repository and the packaged copy is
    ignored -- so editing the registry in place keeps working."""
    repo = tmp_path / "repo"
    (repo / "methods").mkdir(parents=True)
    module = repo / "gigi" / "paths.py"
    module.parent.mkdir()
    module.write_text("", encoding="utf-8")
    (module.parent / "_content" / "methods").mkdir(parents=True)

    assert repo_root(start=module) == repo.resolve()


def test_installed_wheel_falls_back_to_packaged_content(tmp_path):
    """With no checkout above, `gigi/_content/` is the registry."""
    site = tmp_path / "site-packages" / "gigi"
    (site / "_content" / "methods").mkdir(parents=True)
    module = site / "paths.py"
    module.write_text("", encoding="utf-8")

    assert repo_root(start=module) == (site / "_content").resolve()


def test_wheel_is_configured_to_ship_every_content_directory():
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    force_include = config["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for directory in CONTENT:
        assert force_include.get(directory) == f"gigi/_content/{directory}", (
            f"{directory}/ would not ship in the wheel; an installed package would be missing it"
        )


def test_every_content_directory_exists_in_the_checkout():
    for directory in CONTENT:
        assert (repo_root() / directory).is_dir(), f"{directory}/ is missing"


def test_the_sdist_ships_every_content_directory():
    """The third list, after the wheel's force-include and the Dockerfile's COPY.

    `uv build` builds the wheel *from the sdist*, so a directory missing here
    does not ship a quiet gap -- it fails the whole release with "Forced
    include not found". That is exactly what happened on the day of the 0.1.0
    release: `problems/` and `semantics/` were added to the wheel's list and
    forgotten in this one.
    """
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    include = config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]

    for directory in CONTENT:
        assert directory in include, (
            f"{directory}/ is not in the sdist include list, so `uv build` will "
            f"fail when it builds the wheel from the sdist"
        )


def test_the_sdist_ships_the_licence():
    """Apache-2.0 is declared in pyproject and on the container image. A source
    distribution without the text is a licence claim with nothing behind it."""
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    assert "LICENSE" in config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    assert (repo_root() / "LICENSE").is_file(), "LICENSE is missing from the repository"
