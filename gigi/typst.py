"""Typeset one algorithm entry as a Typst document, and optionally a PDF.

The HTML site is for browsing. This is for the other things a registry entry
gets used as: something to print, attach to a review, cite, or hand to a
colleague who will never install anything. Typst renders our stored LaTeX
through the `mitex` package, so the maths a paper needs and the maths the site
shows come from the same field.

Compilation needs the `typst` Python package (`pip install gigi-algo[docs]`).
Rendering the `.typ` source does not.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from gigi import __version__, people, registry
from gigi.harness import verify
from gigi.models import AlgorithmSpec, VerificationReport

MITEX = "@preview/mitex:0.2.6"

PREAMBLE = f'''#import "{MITEX}": mitex, mi
#set page(margin: 2cm, numbering: "1")
#set text(font: ("IBM Plex Sans", "Libertinus Serif"), size: 10pt)
#show raw: set text(font: ("IBM Plex Mono", "DejaVu Sans Mono"), size: 8.5pt)
#show heading.where(level: 1): set text(size: 20pt)
#show heading.where(level: 2): it => {{ v(10pt); it }}
'''

_ESCAPE = str.maketrans({c: f"\\{c}" for c in "#*_@<>$\\[]`"})


def esc(text: object) -> str:
    """Make prose safe inside Typst markup."""
    return str(text).strip().translate(_ESCAPE)


def _math(latex: str | None, fallback: str, block: bool = True) -> str:
    if latex:
        return f"#{'mitex' if block else 'mi'}(`{latex.strip()}`)"
    return f"```\n{fallback.strip()}\n```"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    cells = ", ".join(f"[*{esc(h)}*]" for h in headers)
    body = ",\n  ".join(", ".join(f"[{c}]" for c in row) for row in rows)
    return (
        f"#table(\n  columns: {len(headers)}, stroke: 0.4pt + luma(200), inset: 6pt,\n"
        f"  {cells},\n  {body}\n)\n"
    )


def _names(ids: list[str]) -> str:
    return ", ".join(esc(people.get_person(i).name) if people.exists(i) else esc(i) for i in ids)


def _raw(text: object) -> str:
    """An identifier in a raw span, where Typst escapes nothing."""
    return f"`{str(text).strip()}`"


def _muted(text: str, size: int = 9) -> str:
    return f"#text(size: {size}pt, fill: luma(100))[{text}]"


# --- sections ---------------------------------------------------------------


def _header(spec: AlgorithmSpec) -> list[str]:
    return [
        f"= {esc(spec.name)}",
        _muted(f"{esc(spec.family)} · {esc(spec.maturity.value)} · output: {esc(spec.output.kind.value)}"),
        "",
        esc(spec.problem),
        "",
    ]


def _maths(spec: AlgorithmSpec) -> list[str]:
    maths = spec.maths
    if not (maths.summary or maths.definition):
        return []
    out = ["== Mathematics", esc(maths.summary), ""]
    for formula in filter(None, [maths.definition, *maths.also]):
        out.append(_math(formula.latex, formula.statement))
        if formula.note:
            out += [_muted(esc(formula.note)), ""]
    if maths.invariants:
        out.append("=== Invariants")
        out.append(_table(
            ["invariant", "statement", "checked"],
            [[_raw(i.id),
              _math(i.latex, i.statement, block=False) if i.latex else esc(i.statement),
              "every run" if i.check else "documented"] for i in maths.invariants],
        ))
    if maths.under_determined:
        out.append("=== Where the definition leaves a choice")
        out.append(_table(
            ["question", "defensible answers", "measured"],
            [[esc(c.question),
              " \\\n".join(f"– {esc(ch)}" for ch in c.choices),
              "engines differ: " + ", ".join(_raw(d) for d in c.divergences)
              if c.divergences else ("engines agree" if c.datasets else "untested")]
             for c in maths.under_determined],
        ))
    return out


def _origin(spec: AlgorithmSpec) -> list[str]:
    prov = spec.provenance
    if not (prov.original_authors or prov.original_work):
        return []
    out = ["== Origin"]
    if prov.original_authors:
        year = f" ({prov.introduced})" if prov.introduced else ""
        out += [f"*Original authors{year}.* " + ", ".join(esc(a.name) for a in prov.original_authors), ""]
    if prov.original_work:
        w = prov.original_work
        detail = ", ".join(esc(x) for x in (w.venue, w.year, w.doi) if x is not None)
        out += [f"*Original work.* _{esc(w.title)}_ — {detail}", ""]
    if prov.precursors:
        out.append(_table(
            ["precursor", "authors", "relationship"],
            [[esc(p.name) + (f" ({p.year})" if p.year else ""),
              ", ".join(esc(a) for a in p.authors), esc(p.note or "")] for p in prov.precursors],
        ))
    if prov.attribution_notes:
        out += [_muted(esc(prov.attribution_notes)), ""]
    return out


def _parameters_and_engines(spec: AlgorithmSpec) -> list[str]:
    return [
        "== Parameters",
        _table(
            ["parameter", "type", "Gigi default", "meaning"],
            [[_raw(p.name), esc(p.type),
              "_engine default_" if p.common_default is None else _raw(p.common_default),
              esc(p.description)] for p in spec.parameters],
        ),
        "== Engines",
        _table(["engine", "notes"], [[_raw(n), esc(s.notes or "")] for n, s in spec.engines.items()]),
    ]


def _divergences(spec: AlgorithmSpec, report: VerificationReport | None) -> list[str]:
    if not spec.divergences:
        return []
    checks = {c.divergence_id: c for c in (report.divergence_checks if report else [])}
    out = ["== Divergences"]
    for d in spec.divergences:
        check = checks.get(d.id)
        if check is None:
            evidence = "not checked"
        elif check.observed == "skipped":
            evidence = "skipped: " + esc(check.note)
        elif check.reproduced:
            evidence = "reproduced on " + ", ".join(_raw(x) for x in check.datasets)
        else:
            evidence = "*did not reproduce*: " + esc(check.note)
        found = f" Found by {_names(d.discovered_by)}." if d.discovered_by else ""
        out += [
            f"=== {_raw(d.id)}",
            _muted(f"{esc(d.category.value)} · severity {esc(d.severity.value)} · "
                   f"{', '.join(esc(e) for e in d.engines)}"),
            "",
            esc(d.summary),
            "",
            f"*Consequence.* {esc(d.consequence)}" if d.consequence else "",
            "",
            f"*Evidence.* {evidence}.{found}",
            "",
        ]
    return out


def _verification(report: VerificationReport | None) -> list[str]:
    if report is None:
        return []
    engines = ", ".join(f"{_raw(e)} {esc(report.engine_versions.get(e) or '')}" for e in report.engines)
    return [
        "== Verification",
        f"*{esc(report.status.upper())}* — {esc(report.conclusion)}",
        "",
        f"Engines: {engines}. {len(report.runs)} runs, "
        f"{sum(len(r.invariants) for r in report.runs)} invariant assertions.",
        "",
    ]


def _credits(spec: AlgorithmSpec) -> list[str]:
    credits = spec.credits
    if not credits.everyone():
        return []
    pairs = [("steward", credits.stewards), ("specification", credits.spec_curators),
             ("reference implementation", credits.reference_implementation),
             ("verifier", credits.verifier_authors), ("dataset curation", credits.dataset_curators),
             ("review", credits.reviewers)]
    pairs += [(f"{e} adapter", ids) for e, ids in sorted(credits.adapter_contributors.items())]
    return ["== Gigi contributors", _table(["role", "people"], [[esc(l), _names(ids)] for l, ids in pairs if ids])]


def _footer() -> list[str]:
    return ["", f"#v(1fr){_muted(f'Generated by gigi {esc(__version__)} on {date.today().isoformat()}. '
                                   'Every number here came from running the algorithm.', 8)}"]


# --- public -------------------------------------------------------------------


def render(spec: AlgorithmSpec, report: VerificationReport | None = None) -> str:
    """The full entry as Typst source, one section per question a reader has."""
    lines = [PREAMBLE]
    for section in (
        _header(spec),
        _maths(spec),
        _origin(spec),
        _parameters_and_engines(spec),
        _divergences(spec, report),
        _verification(report),
        _credits(spec),
        _footer(),
    ):
        lines.extend(section)
    return "\n".join(lines) + "\n"


def compile_available() -> bool:
    """Is the optional typst compiler installed?"""
    try:
        import typst  # noqa: F401
    except ImportError:
        return False
    return True


def write(
    algorithm_id: str,
    output_dir: str | Path = "site/typst",
    pdf: bool = False,
    verify_first: bool = True,
) -> list[Path]:
    """Write `<id>.typ`, and `<id>.pdf` when asked and the compiler is installed."""
    spec = registry.load_algorithm(algorithm_id)
    report = verify(spec) if verify_first else None
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    source = directory / f"{algorithm_id}.typ"
    source.write_text(render(spec, report), encoding="utf-8")
    written = [source]

    if pdf:
        if not compile_available():
            raise RuntimeError("PDF output needs the typst package: pip install 'gigi-algo[docs]'")
        import typst

        target = directory / f"{algorithm_id}.pdf"
        target.write_bytes(typst.compile(str(source)))
        written.append(target)
    return written
