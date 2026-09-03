"""The Typst export carries the whole entry, and compiles when a compiler is there."""

from __future__ import annotations

import pytest

from gigi import registry
from gigi.typst import compile_available, esc, render, write

ALGORITHMS = registry.list_algorithms()


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_source_carries_every_section(algorithm_id):
    spec = registry.load_algorithm(algorithm_id)
    source = render(spec)
    for heading in ("= " + spec.name, "== Mathematics", "== Parameters", "== Engines"):
        assert heading in source, f"{algorithm_id}: missing {heading!r}"
    if spec.divergences:
        assert "== Divergences" in source
        for divergence in spec.divergences:
            assert divergence.id in source
    if spec.maths.definition and spec.maths.definition.latex:
        # The stored LaTeX goes through untouched; mitex renders it.
        assert spec.maths.definition.latex.strip() in source
        assert "mitex" in source


def test_prose_is_escaped_but_identifiers_are_not():
    assert esc("a_b #c *d*") == "a\\_b \\#c \\*d\\*"
    source = render(registry.load_algorithm("pagerank"))
    # Identifiers sit in raw spans and must not carry escaped underscores.
    assert "`scores_sum_to_one`" in source
    assert "scores\\_sum" not in source


@pytest.mark.skipif(not compile_available(), reason="typst compiler not installed")
def test_compiles_to_pdf(tmp_path):
    """Needs the network once, to fetch the mitex package."""
    written = write("degree_centrality", tmp_path, pdf=True, verify_first=False)
    pdf = [p for p in written if p.suffix == ".pdf"]
    assert pdf and pdf[0].stat().st_size > 10_000
    assert pdf[0].read_bytes()[:5] == b"%PDF-"


def test_pdf_without_compiler_is_a_clear_error(tmp_path, monkeypatch):
    import gigi.typst as module

    monkeypatch.setattr(module, "compile_available", lambda: False)
    with pytest.raises(RuntimeError, match="gigi-algo\\[docs\\]"):
        write("degree_centrality", tmp_path, pdf=True, verify_first=False)


def test_review_mode_adds_margin_notes_and_checklist():
    from gigi.review import review

    spec = registry.load_algorithm("pagerank")
    plain = render(spec)
    reviewed = render(spec, None, review("pagerank"))
    assert "dashy-todo" not in plain and "#todo(" not in plain
    assert "dashy-todo" in reviewed and "#todo(" in reviewed
    assert "== For the reviewer" in reviewed
    # pagerank has a choice point nothing tests; it should be flagged in the margin
    # prose is escaped for Typst, so the identifier carries an escaped underscore
    assert "convergence\_criterion" in reviewed


def test_review_file_is_named_separately(tmp_path):
    written = write("degree_centrality", tmp_path, review=True)
    assert written[0].name == "degree_centrality.review.typ"


def test_running_header_names_the_algorithm():
    source = render(registry.load_algorithm("degree_centrality"))
    assert "hydra" in source
    assert "[Gigi · Degree Centrality]" in source
