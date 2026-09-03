"""The template must actually work.

`algorithms/_template/` is the first thing a contributor touches, so it is a
worked example rather than a set of blanks — and an example nobody runs is an
example that quietly stops working. This copies the template into a throwaway
registry under a real id and puts it through the same pipeline as any other
algorithm.
"""

from __future__ import annotations

import shutil

import pytest

from gigi.paths import algorithms_dir

TEMPLATE_ID = "template_check"


@pytest.fixture()
def template_registry(tmp_path, monkeypatch):
    """A registry containing only the template, copied under a usable id."""
    source = algorithms_dir() / "_template"
    registry_root = tmp_path / "algorithms"
    destination = registry_root / TEMPLATE_ID
    shutil.copytree(source, destination)

    spec_path = destination / "algorithm.yaml"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "id: my_algorithm", f"id: {TEMPLATE_ID}", 1
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("GIGI_ALGORITHMS_DIR", str(registry_root))
    yield registry_root


def test_template_spec_validates(template_registry):
    from gigi import registry

    spec = registry.load_algorithm(TEMPLATE_ID)
    assert spec.id == TEMPLATE_ID
    assert spec.provenance.original_authors, "the template should demonstrate provenance"
    assert spec.credits.spec_curators, "the template should demonstrate gigi credits"


def test_template_reference_runs(template_registry):
    from gigi.harness import run

    result = run(TEMPLATE_ID, "reference", "tiny-directed")
    assert result.status.value == "ok", result.error
    # tiny-directed: a has degree 3, b has 2, c has 3, over (n - 1) = 2.
    assert result.result.scores == {"a": 1.5, "b": 1.0, "c": 1.5}


def test_template_engines_agree(template_registry):
    """The whole contributor loop, on the template: run every installed engine
    and compare it against the reference."""
    from gigi.adapters import ENGINES
    from gigi.harness import compare

    if not ENGINES["networkx"].available():
        pytest.skip("networkx is not installed")

    runs, comparisons = compare(TEMPLATE_ID, "tiny-directed", engines=["reference", "networkx"])
    assert all(r.status.value == "ok" for r in runs), [r.error for r in runs]
    assert comparisons[0].equivalent, comparisons[0].metrics


def test_template_verifies(template_registry):
    from gigi.harness import verify

    report = verify(TEMPLATE_ID)
    assert report.status == "pass", report.conclusion


def test_template_effective_parameters_are_recorded(template_registry):
    """The example has to demonstrate the habit it is teaching."""
    from gigi.harness import run

    result = run(TEMPLATE_ID, "reference", "tiny-directed")
    assert "normalized" in result.effective_parameters
    assert "degree" in result.effective_parameters
