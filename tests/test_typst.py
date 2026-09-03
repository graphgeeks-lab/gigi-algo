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
