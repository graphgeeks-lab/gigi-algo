"""Whole pages: the registry index, one algorithm, one person.

These decide what goes on a page and in what order. The individual sections
live in `sections.py`; the shell and primitives live in `html.py`.
"""

from __future__ import annotations

from gigi import people, registry
from gigi.adapters import engine_versions
from gigi.graph import list_datasets, load_graph, profile_graph
from gigi.models import AlgorithmSpec, VerificationReport
from gigi.site.html import FROM_ALGORITHM, FROM_INDEX, FROM_PERSON, Links, esc, status_pill, table
from gigi.site.sections import (
    credits_section,
    discovered_by,
    family_section,
    maths_section,
    person_body,
    provenance_section,
    relationships_section,
)

def index_body(
    specs: list[AlgorithmSpec],
    reports: dict[str, VerificationReport],
    links: Links = FROM_INDEX,
) -> str:
    """The registry front page: algorithms, families, fixtures, engines, people."""
    installed = engine_versions()
    rows = []
    for spec in specs:
        report = reports.get(spec.id)
        href = links.to_algorithm(spec.id)
        rows.append(
            [
                f'<a href="{esc(href)}"><code>{esc(spec.id)}</code></a>',
                esc(spec.family),
                f'<span class="pill">{esc(spec.maturity.value)}</span>',
                ", ".join(f"<code>{esc(e)}</code>" for e in registry.implemented_engines(spec.id)),
                str(len(spec.divergences)),
                status_pill(report.status) if report else "-",
            ]
        )

    dataset_rows = []
    for dataset_id in list_datasets():
        graph = load_graph(dataset_id)
        profile = profile_graph(graph)
        features = [name for name, on in graph.metadata.features.items() if on] or ["plain"]
        dataset_rows.append(
            [
                f"<code>{esc(dataset_id)}</code>",
                str(profile.node_count),
                str(profile.edge_count),
                ", ".join(f"<code>{esc(f)}</code>" for f in features),
                esc(graph.metadata.description.strip()),
            ]
        )

    engine_rows = [
        [f"<code>{esc(name)}</code>", esc(version or "unknown")]
        for name, version in installed.items()
    ]

    return f"""
<h1>Gigi</h1>
<p class="lede">The same named graph algorithm can return different answers on
different engines, because defaults and semantics differ. Gigi writes those
differences down, then runs them to prove they are real.</p>

<h2>Algorithms</h2>
{table(["algorithm", "family", "maturity", "engines", "divergences", "verification"], rows)}

<h2>Families</h2>
<p class="lede">A family is a question, not a label. An algorithm belongs to one
when it answers that question -- which is what makes the taxonomy useful for
choosing within it rather than merely filing things.</p>
{families_table(links)}

<h2>Adversarial fixtures</h2>
<p class="lede">Small, deterministic graphs chosen because each one puts pressure
on a specific semantic decision.</p>
{table(["dataset", "nodes", "edges", "features", "why it exists"], dataset_rows)}

<h2>Engines in this build</h2>
{table(["engine", "version"], engine_rows)}

<h2>People</h2>
<p class="lede">Who did the work here. Separate from who created the algorithms,
which is recorded per algorithm under Origin.</p>
{people_table(links)}
"""


def families_table(links: Links) -> str:
    """The taxonomy, one row per family."""
    rows = []
    for family in registry.list_families():
        members = registry.algorithms_in_family(family.id)
        parent = registry.load_family(family.parent).name if family.parent else ""
        rows.append(
            [
                f"<code>{esc(family.id)}</code>",
                esc(family.question),
                esc(parent),
                ", ".join(
                    f'<a href="{esc(links.to_algorithm(a))}"><code>{esc(a)}</code></a>'
                    for a in members
                )
                or '<span class="pill">none yet</span>',
            ]
        )
    return table(["family", "the question it answers", "within", "algorithms"], rows)


def people_table(links: Links) -> str:
    """Contributors, with what each has worked on."""
    rows = []
    for person in people.list_people():
        profile = people.profile(person.id)
        rows.append(
            [
                f'<a href="{esc(links.to_person(person.id))}">{esc(person.name)}</a>',
                ", ".join(f"<code>{esc(role.value)}</code>" for role in person.roles),
                ", ".join(
                    f'<a href="{esc(links.to_algorithm(a))}"><code>{esc(a)}</code></a>'
                    for a in profile.algorithms
                ),
                str(len(profile.discoveries)),
            ]
        )
    return table(["person", "roles", "algorithms", "divergences found"], rows)

def algorithm_body(
    spec: AlgorithmSpec,
    report: VerificationReport | None,
    links: Links = FROM_ALGORITHM,
    heading: str = "h1",
) -> str:
    """One algorithm, in the order a reader needs it: what it is for, where it
    sits, the maths, where it came from, how to call it, what the engines did,
    what it is like, and who built the entry."""
    parameters = table(
        ["parameter", "type", "gigi default", "meaning"],
        [
            [
                f"<code>{esc(p.name)}</code>",
                esc(p.type),
                "<em>engine default</em>" if p.common_default is None else f"<code>{esc(p.common_default)}</code>",
                esc(p.description.strip()),
            ]
            for p in spec.parameters
        ],
    )

    engines = table(
        ["engine", "supported", "notes"],
        [
            [f"<code>{esc(name)}</code>", "yes" if support.supported else "no", esc(support.notes or "")]
            for name, support in spec.engines.items()
        ],
    )

    divergence_blocks = []
    checks = {c.divergence_id: c for c in (report.divergence_checks if report else [])}
    for divergence in spec.divergences:
        check = checks.get(divergence.id)
        if check is None:
            evidence = '<span class="pill">not checked</span>'
        elif check.observed == "skipped":
            evidence = f'<span class="pill warn">skipped</span> {esc(check.note)}'
        elif check.reproduced:
            error = check.metrics.get("max_abs_error")
            evidence = (
                f'<span class="pill ok">reproduced</span> on '
                f'{", ".join(f"<code>{esc(d)}</code>" for d in check.datasets)}, '
                f'{" vs ".join(f"<code>{esc(e)}</code>" for e in check.engines)}'
                + (f", max abs error <code>{error:.3e}</code>" if error is not None else "")
            )
        else:
            evidence = f'<span class="pill bad">did not reproduce</span> {esc(check.note)}'

        divergence_blocks.append(
            f"""<div class="card sev-{esc(divergence.severity.value)}">
<div class="tags"><code>{esc(divergence.id)}</code>
<span class="pill">{esc(divergence.category.value)}</span>
<span class="pill">severity {esc(divergence.severity.value)}</span>
{" ".join(f'<span class="pill">{esc(e)}</span>' for e in divergence.engines)}</div>
<p>{esc(divergence.summary.strip())}</p>
{f"<p><strong>Consequence.</strong> {esc(divergence.consequence.strip())}</p>" if divergence.consequence else ""}
<p class="mono">{evidence}</p>
{discovered_by(divergence, links)}
</div>"""
        )

    verification = ""
    if report:
        run_rows = [
            [
                f"<code>{esc(r.dataset_id)}</code>",
                f"<code>{esc(r.engine)}</code>",
                esc(r.engine_version or "-"),
                esc(r.status.value),
                f"{r.total_duration_ms:.1f}",
                "<br>".join(
                    f"<code>{esc(k)}={esc(v)}</code>" for k, v in r.effective_parameters.items()
                ),
            ]
            for r in report.runs
        ]
        undeclared = (
            "".join(
                f'<p class="bad">Undeclared difference: <code>{esc(d.engine_a)}</code> vs '
                f'<code>{esc(d.engine_b)}</code> on <code>{esc(d.dataset_id)}</code></p>'
                for d in report.undeclared_differences
            )
            or '<p class="ok">No undeclared differences: with every ambiguous parameter '
            "pinned, all engines agreed within tolerance.</p>"
        )
        verification = f"""
<h2>Verification {status_pill(report.status)}</h2>
<p class="lede">{esc(report.conclusion)}</p>
{undeclared}
<h3>Effective parameters, per run</h3>
<p class="lede">What the engine actually used, as opposed to what was requested.</p>
{table(["dataset", "engine", "version", "status", "ms", "effective parameters"], run_rows)}
"""

    return f"""
<p><a href="{esc(links.index)}">&larr; registry</a></p>
<{heading} id="algorithm-{esc(spec.id)}">{esc(spec.name)}</{heading}>
<p class="lede">{esc(spec.problem.strip())}</p>
<p><span class="pill">{esc(spec.family)}</span>
<span class="pill">{esc(spec.maturity.value)}</span>
<span class="pill">output: {esc(spec.output.kind.value)}</span>
<span class="pill">{"deterministic" if spec.deterministic else "stochastic"}</span></p>

{family_section(spec, links)}
{maths_section(spec)}
{provenance_section(spec)}

<h2>Parameters</h2>
{parameters}

<h2>Engines</h2>
{engines}

<h2>Divergences</h2>
{"".join(divergence_blocks) or "<p>None recorded yet.</p>"}
{verification}
{relationships_section(spec, links)}
{credits_section(spec, links)}
"""
