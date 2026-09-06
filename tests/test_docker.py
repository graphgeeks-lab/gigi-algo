"""The Dockerfile cannot drift from the package it builds.

None of this needs Docker. It needs the Dockerfile to keep agreeing with
`pyproject.toml`, `gigi/paths.py` and the CLI, which is where it will actually
go wrong: the image builds fine while quietly shipping half a registry.

That is not hypothetical. `problems/` and `semantics/` were added to the
registry and forgotten in `pyproject.toml`, so every installed wheel was missing
them and nothing noticed. The builder stage has its own `COPY` list -- a third
place the same fact is written -- so it gets the same treatment.
"""

from __future__ import annotations

import re
import tomllib

import pytest

from gigi.paths import CONTENT_DIRECTORIES, repo_root

DOCKERFILE = repo_root() / "Dockerfile"
DOCKERIGNORE = repo_root() / ".dockerignore"


@pytest.fixture(scope="module")
def dockerfile() -> str:
    if not DOCKERFILE.is_file():
        pytest.fail("Dockerfile is missing")
    return DOCKERFILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pyproject() -> dict:
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


# --- the registry has to reach the image ---------------------------------------


@pytest.mark.parametrize("directory", CONTENT_DIRECTORIES)
def test_the_builder_copies_every_content_directory(dockerfile, directory):
    """A directory the builder does not copy is missing from the wheel it
    builds, and the image starts anyway with a registry full of holes."""
    assert re.search(rf"^COPY .*\b{directory}/", dockerfile, re.M), (
        f"{directory}/ is in gigi/paths.py but the Dockerfile never copies it, "
        f"so the wheel built inside the image would not contain it"
    )


def test_the_dockerignore_does_not_exclude_content(dockerfile):
    """`.dockerignore` runs before `COPY`, so an over-broad pattern silently
    empties a directory the builder thinks it copied."""
    if not DOCKERIGNORE.is_file():
        pytest.skip("no .dockerignore")

    patterns = [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for directory in CONTENT_DIRECTORIES:
        assert directory not in patterns, (
            f".dockerignore excludes {directory}/, which the builder needs"
        )


# --- what it runs --------------------------------------------------------------


def test_the_entrypoint_is_the_cli(dockerfile):
    assert 'ENTRYPOINT ["gigi"]' in dockerfile, (
        "the entrypoint should be `gigi` so that `docker run <image> verify` "
        "works as a subcommand rather than needing a shell"
    )


def test_the_default_command_is_a_real_command(dockerfile):
    """`CMD ["mcp"]` is only useful if `gigi mcp` exists. A renamed command
    would leave an image whose default invocation fails."""
    from gigi.cli import app

    match = re.search(r'^CMD \["([a-z-]+)"\]', dockerfile, re.M)
    assert match, "no CMD found"

    command = match.group(1)
    names = {c.name or c.callback.__name__ for c in app.registered_commands}
    assert command in names, f"CMD is {command!r}, which is not a gigi command"


def test_the_healthcheck_is_a_real_command(dockerfile):
    """A healthcheck that cannot run reports unhealthy forever, which is worse
    than having none."""
    from gigi.cli import app

    match = re.search(r'CMD \["gigi", "([a-z-]+)"\]', dockerfile)
    if match is None:
        pytest.skip("no healthcheck")

    names = {c.name or c.callback.__name__ for c in app.registered_commands}
    assert match.group(1) in names


# --- what it installs ----------------------------------------------------------


def test_it_installs_the_extra_it_names(dockerfile, pyproject):
    """The image installs `[all]` so that `gigi verify` can actually run every
    backend. If that extra were renamed, the image would build and then be
    unable to verify anything."""
    match = re.search(r'pip install [^\n]*\.whl\)\[(\w+)\]', dockerfile)
    assert match, "the runtime stage should install the wheel with an extra"

    extra = match.group(1)
    assert extra in pyproject["project"]["optional-dependencies"], (
        f"the Dockerfile installs [{extra}], which pyproject.toml does not define"
    )


def test_every_backend_is_reachable_in_the_image(dockerfile, pyproject):
    """`gigi verify` compares backends against each other. An image missing one
    silently verifies less than it appears to."""
    from gigi.registry import BACKEND_NAMES

    match = re.search(r'pip install [^\n]*\.whl\)\[(\w+)\]', dockerfile)
    installed = " ".join(pyproject["project"]["optional-dependencies"][match.group(1)])

    # `reference` is Gigi itself; every other backend needs its library present.
    aliases = {"igraph": "python-igraph", "sklearn": "scikit-learn"}
    for backend in BACKEND_NAMES:
        if backend == "reference":
            continue
        assert aliases.get(backend, backend) in installed, (
            f"the {backend} backend has no library in the image's extra"
        )


def test_python_matches_what_ci_tests_on(dockerfile):
    """An image on a different Python from CI is a configuration nobody
    tested."""
    ci = (repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    tested = set(re.findall(r'python-version: "([\d.]+)"', ci))
    image = set(re.findall(r"^FROM python:([\d.]+)-", dockerfile, re.M))

    assert image, "no python base image found"
    assert image <= tested, f"image builds on {image}, CI tests {tested}"


def test_it_does_not_run_as_root(dockerfile):
    """An agent runtime starts this unattended, which is exactly when it
    matters."""
    assert re.search(r"^USER (?!root)", dockerfile, re.M), "no non-root USER"


def test_a_version_tag_publishes_latest_too():
    """The public quick-start uses :latest, so the tag workflow must create it."""
    workflow = (repo_root() / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8")
    assert "type=raw,value=latest" in workflow
