"""An installed wheel is a complete registry, not just the code.

The build smoke in the release workflow proves this against a real wheel.
These are the cheaper, every-push versions of the same concern.
"""

from __future__ import annotations

import tomllib

from gigi.paths import repo_root

CONTENT = ("algorithms", "datasets", "families", "people")


def test_checkout_wins_over_packaged_content(tmp_path):
    """In a checkout, walking up finds the repository and the packaged copy is
    ignored -- so editing the registry in place keeps working."""
    repo = tmp_path / "repo"
    (repo / "algorithms").mkdir(parents=True)
    module = repo / "gigi" / "paths.py"
    module.parent.mkdir()
    module.write_text("", encoding="utf-8")
    (module.parent / "_content" / "algorithms").mkdir(parents=True)

    assert repo_root(start=module) == repo.resolve()


def test_installed_wheel_falls_back_to_packaged_content(tmp_path):
    """With no checkout above, `gigi/_content/` is the registry."""
    site = tmp_path / "site-packages" / "gigi"
    (site / "_content" / "algorithms").mkdir(parents=True)
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
