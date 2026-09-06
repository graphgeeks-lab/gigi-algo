"""A release must be describable before it can be cut.

The release workflow checks these on the tag. Checking them here too means a
mismatch is caught on every push, not on release day.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib

import yaml

import gigi
from gigi.paths import repo_root

ROOT = repo_root()


def _pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def test_the_package_reports_the_pyproject_version():
    """gigi.__version__ is read from installed metadata, so an editable install
    must agree with pyproject.toml. If this fails, reinstall (`uv pip install -e .`)
    -- or, if it fails in CI, the version was bumped without the wheel being rebuilt."""
    assert gigi.__version__ == _pyproject_version()


def test_citation_carries_the_same_version():
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)\s*$", text, re.M)
    assert match, "CITATION.cff has no version line"
    assert match.group(1) == _pyproject_version(), (
        "CITATION.cff disagrees with pyproject.toml; run scripts/sync-version.py"
    )


def test_sync_script_agrees_in_check_mode():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync-version.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_citation_is_valid_yaml_with_the_required_fields():
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    for field in ("cff-version", "title", "version", "authors", "repository-code"):
        assert field in citation, f"CITATION.cff is missing {field!r}"


def test_changelog_has_an_unreleased_section_and_the_current_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[Unreleased\]", text, re.M), "CHANGELOG.md needs an [Unreleased] section"

    versions = re.findall(r"^## \[(\d[^\]]*)\]", text, re.M)
    assert versions, "CHANGELOG.md has no versioned sections"
    current = _pyproject_version()
    # The current version is either already released (has a section) or is
    # what [Unreleased] will become. Anything *newer* than pyproject in the
    # changelog is a section for a version that does not exist.
    for version in versions:
        assert _key(version) <= _key(current), (
            f"CHANGELOG.md describes {version}, newer than pyproject.toml's {current}"
        )


def test_changelog_sections_are_substantial():
    """The workflow turns a section into release notes verbatim, and refuses
    sections under 40 characters. Catch that here, earlier."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for match in re.finditer(r"^## \[(\d[^\]]*)\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S):
        version, body = match.group(1), match.group(2).strip()
        assert len(body) >= 40, f"CHANGELOG section [{version}] is too short to be release notes"


def test_release_workflow_is_driven_by_version_tags():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as boolean True.
    trigger = workflow.get("on", workflow.get(True))
    assert trigger["push"]["tags"] == ["v*"]
    assert set(workflow["jobs"]) == {"check", "build", "publish", "release"}
    assert workflow["jobs"]["release"]["needs"] == ["check", "publish"], (
        "the Release page must be created after publishing, never before"
    )
    assert "id-token" in workflow["jobs"]["publish"]["permissions"], "trusted publishing needs id-token: write"


def _key(version: str) -> tuple:
    """Enough of PEP 440 to order our own versions: release tuple, then a
    pre-release marker that sorts below the final."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", version)
    assert match, f"unexpected version format {version!r}"
    major, minor, patch, kind, number = match.groups()
    pre = {"a": 0, "b": 1, "rc": 2, None: 3}[kind]
    return (int(major), int(minor), int(patch), pre, int(number or 0))
