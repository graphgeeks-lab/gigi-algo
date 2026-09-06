"""Page shell, link scheme, and the handful of primitives every section
renders through.

Kept apart from `sections.py` and `pages.py` so that someone asking "what does
an algorithm page show?" does not have to scroll past 120 lines of CSS to find
out. Nothing here knows what a graph algorithm is.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone

from gigi import __version__


@dataclass(frozen=True)
class Links:
    """Where one page points at another. The multi-page site uses relative
    paths; the single-file build uses anchors into the same document."""

    algorithm: str
    person: str
    index: str

    def to_algorithm(self, method_id: str) -> str:
        return self.algorithm.format(id=method_id)

    def to_person(self, person_id: str) -> str:
        return self.person.format(id=person_id)


FROM_INDEX = Links(algorithm="algorithms/{id}.html", person="people/{id}.html", index="#top")
FROM_ALGORITHM = Links(
    algorithm="{id}.html", person="../people/{id}.html", index="../index.html"
)
FROM_PERSON = Links(
    algorithm="../algorithms/{id}.html", person="{id}.html", index="../index.html"
)
INLINE = Links(algorithm="#algorithm-{id}", person="#person-{id}", index="#top")

# This is a small public registry, not a themed application. It deliberately
# stays light and uses system fonts: it reads well, loads without a third-party
# font request, and makes generated evidence feel like a document rather than a
# dashboard.
CSS = """
:root {
  color-scheme: light;
  --bg:#ffffff; --panel:#f8fafc; --fg:#172033; --muted:#5d6778; --line:#d9e0ea;
  --accent:#1d4ed8; --ok:#087443; --bad:#b42318; --warn:#8a5b00;
  --sans:ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono:ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.65 var(--sans); }
.wrap { max-width:62rem; margin:0 auto; padding:3.5rem 1.5rem 5rem;
  display:flex; flex-direction:column; gap:0; }
a { color:var(--accent); text-underline-offset:.15em; }
a:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
h1 { font-size:2.1rem; font-weight:600; margin:0 0 .5rem; letter-spacing:-.03em;
  text-wrap:balance; }
h2 { font-size:1.2rem; font-weight:600; margin:3rem 0 .85rem; letter-spacing:-.015em;
  text-wrap:balance; }
h3 { font-family:var(--mono); font-size:.78rem; font-weight:500; margin:1.75rem 0 .5rem;
  color:var(--muted); text-transform:uppercase; letter-spacing:.09em; }
p { margin:0 0 1rem; max-width:62ch; }
p.lede { color:var(--muted); margin:0 0 1.75rem; }
table { border-collapse:collapse; width:100%; font-size:.88rem;
  font-variant-numeric:tabular-nums; }
.scroll { overflow-x:auto; }
th, td { text-align:left; padding:.55rem .7rem; border-bottom:1px solid var(--line);
  vertical-align:top; }
tbody tr:last-child td { border-bottom:none; }
th { font-family:var(--mono); font-weight:500; color:var(--muted); font-size:.72rem;
  text-transform:uppercase; letter-spacing:.08em; white-space:nowrap; }
code, .mono { font-family:var(--mono); font-size:.85em; }
.pill { display:inline-block; padding:.08rem .5rem; border-radius:999px;
  font-family:var(--mono); font-size:.72rem; border:1px solid var(--line);
  color:var(--muted); }
.pill.ok { color:var(--ok); border-color:currentColor; }
.pill.bad { color:var(--bad); border-color:currentColor; }
.pill.warn { color:var(--warn); border-color:currentColor; }
.ok { color:var(--ok); } .bad { color:var(--bad); } .warn { color:var(--warn); }
/* Severity is encoded in the stripe as well as the word, so a page of
   divergences can be triaged without reading it. */
.card { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--muted);
  border-radius:4px; padding:1rem 1.15rem; margin:.9rem 0; }
.card > :last-child { margin-bottom:0; }
.card.sev-high, .card.sev-critical { border-left-color:var(--bad); }
.card.sev-medium { border-left-color:var(--warn); }
.card.sev-low, .card.sev-info { border-left-color:var(--muted); }
.card.formula { border-left-color:var(--accent); }
.card.formula pre { margin:0 0 .6rem; font-family:var(--mono); font-size:.86rem;
  line-height:1.55; white-space:pre-wrap; overflow-x:auto; }
.math { margin:.25rem 0 .8rem; overflow-x:auto; text-align:center; }
.math code { display:block; padding:.35rem 0; white-space:nowrap; }
.math-source { color:var(--muted); font-size:.82rem; }
.math-source summary { cursor:pointer; width:max-content; }
.math-source code { display:block; margin-top:.45rem; overflow-x:auto; white-space:pre-wrap; }
.tags { display:flex; flex-wrap:wrap; gap:.35rem; align-items:center; margin-bottom:.6rem; }
footer { margin-top:4.5rem; color:var(--muted); font-size:.8rem;
  border-top:1px solid var(--line); padding-top:1rem; }
"""

# KaTeX turns the LaTeX stored in method specs into accessible browser math.
# It is intentionally limited to formula elements; prose and code blocks are
# never scanned or modified. The source remains in the element as a fallback
# when a visitor is offline or their browser blocks external scripts.
MATH_RENDERER = """<link rel="stylesheet"
href="https://cdn.jsdelivr.net/npm/katex@0.18.5/dist/katex.min.css"
integrity="sha384-2dNi/m6JtSiviznrOIZ5fTiZ5As0In2QwkuXSgoqcQtCNplvJAbt+jveeN+8en73"
crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.18.5/dist/katex.min.js"
integrity="sha384-TTF8eEsEKInX2meLzP5V1z/npGYIElXYGksx93f0qBZHu6IL3PdzVB8objytx+TR"
crossorigin="anonymous" onload="document.querySelectorAll('.math[data-latex]').forEach(
function(element) { katex.render(element.dataset.latex, element, {displayMode: true,
throwOnError: false}); });"></script>"""


def esc(value: object) -> str:
    return html.escape(str(value))


def page(title: str, body: str) -> str:
    """Wrap a body in the document shell."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>{MATH_RENDERER}<style>{CSS}</style></head>
<body><div class="wrap" id="top">{body}
<footer>Gigi method registry &middot; generated by gigi {esc(__version__)} on {generated}.
Verification evidence is generated from executable checks on this revision.</footer>
</div></body></html>
"""


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def status_pill(status: str) -> str:
    css = "ok" if status == "pass" else "bad"
    return f'<span class="pill {css}">{esc(status)}</span>'
