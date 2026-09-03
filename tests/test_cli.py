"""Thin integration tests. The CLI should have no logic worth testing here --
if one of these ever needs a clever assertion, the logic is in the wrong file.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from gigi.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("GIGI_STATE_DIR", str(tmp_path / ".gigi"))


def test_list():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "pagerank" in result.output


def test_show():
    result = runner.invoke(app, ["show", "pagerank"])
    assert result.exit_code == 0
    assert "damping" in result.output


def test_inspect():
    result = runner.invoke(app, ["inspect", "dangling-small"])
    assert result.exit_code == 0
    assert "dangling_node_count" in result.output


def test_run_writes_state_and_prints_scores():
    from gigi import runstore

    result = runner.invoke(
        app, ["run", "pagerank", "--graph", "tiny-directed", "--engine", "reference"]
    )
    assert result.exit_code == 0
    assert runstore.last_run() is not None


def test_compare():
    result = runner.invoke(app, ["compare", "pagerank", "--graph", "weighted-small"])
    assert result.exit_code == 0
    assert "baseline" in result.output


def test_verify():
    result = runner.invoke(app, ["verify", "pagerank"])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_site_build(tmp_path):
    output = tmp_path / "site"
    result = runner.invoke(app, ["site", "build", "--output", str(output)])
    assert result.exit_code == 0
    assert (output / "index.html").is_file()
    assert (output / "algorithms" / "pagerank.html").is_file()


def test_origin():
    result = runner.invoke(app, ["origin", "pagerank"])
    assert result.exit_code == 0
    assert "Original authors" in result.output
    assert "Gigi contributors" in result.output


def test_people():
    result = runner.invoke(app, ["people"])
    assert result.exit_code == 0
    assert "dennis-irorere" in result.output


def test_person():
    result = runner.invoke(app, ["person", "dennis-irorere"])
    assert result.exit_code == 0
    assert "Divergences found" in result.output


def test_site_build_writes_people_pages(tmp_path):
    output = tmp_path / "site"
    result = runner.invoke(app, ["site", "build", "--output", str(output)])
    assert result.exit_code == 0
    assert (output / "people" / "dennis-irorere.html").is_file()


def test_maths():
    result = runner.invoke(app, ["maths", "pagerank"])
    assert result.exit_code == 0
    assert "Invariants" in result.output
    assert "scores_sum_to_one" in result.output


def test_families():
    result = runner.invoke(app, ["families"])
    assert result.exit_code == 0
    assert "centrality" in result.output


def test_family():
    result = runner.invoke(app, ["family", "centrality"])
    assert result.exit_code == 0
    assert "pagerank" in result.output


def test_export_is_valid_json_with_everything_in_it(tmp_path):
    import json

    path = tmp_path / "registry.json"
    result = runner.invoke(app, ["export", "--output", str(path)])
    assert result.exit_code == 0

    document = json.loads(path.read_text(encoding="utf-8"))
    assert {"gigi_version", "families", "people", "algorithms", "datasets"} <= set(document)

    pagerank = next(a for a in document["algorithms"] if a["id"] == "pagerank")
    # The alias, not the field name: the export is what an outside consumer sees.
    assert "gigi" in pagerank
    assert pagerank["maths"]["invariants"]
    assert pagerank["provenance"]["original_authors"]
    assert pagerank["relationships"]


def test_review_separates_machine_checks_from_human_ones():
    result = runner.invoke(app, ["review", "pagerank"])
    assert result.exit_code == 0, result.output
    assert "Settled by machine" in result.output
    assert "By eye" in result.output
    # The definition is printed so a reviewer can check it against reference.py.
    assert "r(v)" in result.output
