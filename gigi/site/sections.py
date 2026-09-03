"""The sections of an algorithm page, and the person profile.

One function per section, each answering a single question a reader has:
where does this sit, what is the maths, where did it come from, what is it
like, who built it. They are separate functions so that changing what a page
says about provenance cannot accidentally change what it says about maths.
"""

from __future__ import annotations

from gigi import people, registry
from gigi.models import AlgorithmSpec
from gigi.site.html import FROM_PERSON, Links, esc, status_pill, table

def discovered_by(divergence, links: Links) -> str:
    """Finding a divergence is a contribution in its own right, and the person
    who found it is usually not the person who wrote the adapter."""
    if not divergence.discovered_by:
        return ""
    names = ", ".join(
        f'<a href="{esc(links.to_person(i))}">{esc(people.get_person(i).name)}</a>'
        if people.exists(i)
        else esc(i)
        for i in divergence.discovered_by
    )
    when = f", {esc(divergence.reported)}" if divergence.reported else ""
    return f'<p class="lede">Found by {names}{when}.</p>'


def person_body(profile: people.Profile, links: Links = FROM_PERSON, heading: str = "h1") -> str:
    """A contribution lineage, not a score.

    A points total rewards volume and invites gaming; "wrote the reference
    implementation for PageRank and found the NetworkX weight divergence" is
    something a person can actually put their name to.
    """
    person = profile.person
    identity = []
    for label, template, handle in (
        ("GitHub", "https://github.com/{}", person.github),
        ("LinkedIn", "https://www.linkedin.com/in/{}", person.linkedin),
        ("ORCID", "https://orcid.org/{}", person.orcid),
        ("Website", "{}", person.website),
    ):
        if handle:
            identity.append(f'<a href="{esc(template.format(handle))}">{label}</a>')
    for label, url in sorted(person.links.items()):
        identity.append(f'<a href="{esc(url)}">{esc(label)}</a>')

    def _rows(items):
        return [
            [
                f'<a href="{esc(links.to_algorithm(c.algorithm_id))}">'
                f"<code>{esc(c.algorithm_id)}</code></a>",
                esc(c.role),
                f"<code>{esc(c.detail)}</code>" if c.detail else "",
            ]
            for c in items
        ]

    contributions = (
        table(["algorithm", "contribution", "detail"], _rows(profile.contributions))
        if profile.contributions
        else "<p>Nothing recorded yet.</p>"
    )
    discoveries = (
        table(["algorithm", "kind", "divergence"], _rows(profile.discoveries))
        if profile.discoveries
        else "<p>None recorded.</p>"
    )

    return f"""
<p><a href="{esc(links.index)}">&larr; registry</a></p>
<{heading} id="person-{esc(person.id)}">{esc(person.name)}</{heading}>
<p class="lede">{esc(person.affiliation or "")}{" &middot; " if person.affiliation and identity else ""}{" &middot; ".join(identity)}</p>
<p class="tags">{" ".join(f'<span class="pill">{esc(r.value)}</span>' for r in person.roles)}</p>
{f'<p class="lede">Interests: {", ".join(esc(i) for i in person.interests)}</p>' if person.interests else ""}

<h2>Contributions</h2>
{contributions}

<h2>Divergences found</h2>
<p class="lede">Differences between engines that this person identified and
turned into a reproducible, CI-checked claim.</p>
{discoveries}
"""


def maths_section(spec: AlgorithmSpec) -> str:
    """The maths, shown as plain-text statements with the LaTeX beside them.

    No typesetting library: KaTeX needs a stylesheet and font files, and this
    page has to render anywhere it is served from. The plain statement is what
    a reader needs; the LaTeX is what a paper needs; both are in the spec.
    """
    maths = spec.maths
    if not maths.summary and not maths.definition:
        return ""

    parts = ["<h2>Mathematics</h2>"]
    if maths.summary:
        parts.append(f'<p class="lede">{esc(maths.summary.strip())}</p>')

    for formula in filter(None, [maths.definition, *maths.also]):
        latex = (
            f'<p class="latex"><span>LaTeX</span><code>{esc(formula.latex.strip())}</code></p>'
            if formula.latex
            else ""
        )
        note = f"<p>{esc(formula.note.strip())}</p>" if formula.note else ""
        parts.append(
            f'<div class="card formula"><pre>{esc(formula.statement.rstrip())}</pre>'
            f"{latex}{note}</div>"
        )

    if maths.invariants:
        rows = [
            [
                f"<code>{esc(i.id)}</code>",
                esc(i.statement),
                '<span class="pill ok">checked on every run</span>'
                if i.check
                else '<span class="pill">documented</span>',
                esc(i.note.strip() if i.note else ""),
            ]
            for i in maths.invariants
        ]
        parts.append(
            "<h3>Invariants</h3>"
            '<p class="lede">Properties the result must satisfy. The checked ones are '
            "asserted on every engine and every fixture, so the maths is executed "
            "rather than believed.</p>" + table(["id", "statement", "status", "note"], rows)
        )

    if maths.under_determined:
        rows = []
        for choice in maths.under_determined:
            outcome = []
            if choice.divergences:
                outcome.append(
                    '<span class="pill bad">engines differ</span> '
                    + ", ".join(f"<code>{esc(d)}</code>" for d in choice.divergences)
                )
            elif choice.datasets:
                outcome.append('<span class="pill ok">engines agree</span>')
            outcome.extend(f"<code>{esc(d)}</code>" for d in choice.datasets)
            rows.append(
                [
                    esc(choice.question),
                    "<br>".join(f"&bull; {esc(c)}" for c in choice.choices),
                    "<br>".join(outcome),
                ]
            )
        parts.append(
            "<h3>Where the definition leaves a choice</h3>"
            '<p class="lede">Divergences record where engines <em>did</em> differ. '
            "These record where they <em>could</em> — which is what lets a new engine "
            "be assessed before it is ever run.</p>"
            + table(["question", "defensible answers", "what we measured"], rows)
        )

    return "".join(parts)


def relationships_section(spec: AlgorithmSpec, links: Links) -> str:
    """Typed edges to other algorithms, with the conditions that make a
    substitution legitimate."""
    if not spec.relationships:
        return ""
    known = set(registry.list_algorithms())
    rows = []
    for relationship in spec.relationships:
        target = relationship.algorithm
        label = (
            f'<a href="{esc(links.to_algorithm(target))}"><code>{esc(target)}</code></a>'
            if target in known
            else f'<code>{esc(target)}</code> <span class="pill">not yet in the registry</span>'
        )
        rows.append(
            [
                f'<code>{esc(relationship.kind.value)}</code>',
                label,
                esc(relationship.condition.strip()) if relationship.condition else "",
                esc(relationship.note.strip() if relationship.note else ""),
            ]
        )
    return (
        "<h2>Related algorithms</h2>"
        '<p class="lede">Typed edges, not a "see also" list. Knowing that PageRank '
        "generalises eigenvector centrality, and under what condition the two "
        "coincide, is something a reader — or an agent — can act on.</p>"
        + table(["relationship", "algorithm", "coincides when", "note"], rows)
    )


def family_section(spec: AlgorithmSpec, links: Links) -> str:
    """Where this sits in the taxonomy, and what else answers the same question."""
    if not registry.family_exists(spec.family):
        return ""
    lineage = registry.family_lineage(spec.family)
    family = lineage[-1]
    trail = " &rarr; ".join(esc(f.name) for f in lineage)
    siblings = [a for a in registry.algorithms_in_family(family.id) if a != spec.id]
    also = (
        " Also here: "
        + ", ".join(
            f'<a href="{esc(links.to_algorithm(a))}"><code>{esc(a)}</code></a>'
            for a in siblings
        )
        + "."
        if siblings
        else ""
    )
    return f"""<h2>Family</h2>
<div class="card"><div class="tags"><span class="pill">{trail}</span></div>
<p><strong>{esc(family.question)}</strong></p>
<p>{esc(family.summary.strip())}{also}</p></div>"""


def provenance_section(spec: AlgorithmSpec) -> str:
    """Where the algorithm came from -- kept visually distinct from who
    implemented it here, because they are different claims with different
    kinds of evidence."""
    provenance = spec.provenance
    if not provenance.original_authors and not provenance.original_work:
        return ""

    parts = ["<h2>Origin</h2>"]

    if provenance.original_authors:
        authors = "".join(
            f"<li>{esc(a.name)}"
            + (f' <span class="pill">ORCID {esc(a.orcid)}</span>' if a.orcid else "")
            + (f'<br><span class="lede">{esc(a.note.strip())}</span>' if a.note else "")
            + "</li>"
            for a in provenance.original_authors
        )
        introduced = f" ({provenance.introduced})" if provenance.introduced else ""
        parts.append(f"<h3>Original authors{esc(introduced)}</h3><ul>{authors}</ul>")

    work = provenance.original_work
    if work:
        title = esc(work.title)
        if work.url:
            title = f'<a href="{esc(work.url)}">{title}</a>'
        elif work.doi:
            title = f'<a href="https://doi.org/{esc(work.doi)}">{title}</a>'
        detail = ", ".join(
            esc(bit) for bit in (work.venue, work.year, work.doi) if bit is not None
        )
        parts.append(f"<h3>Original work</h3><p>{title}<br><span class='lede'>{detail}</span></p>")

    if provenance.precursors:
        rows = [
            [
                esc(p.name) + (f" ({p.year})" if p.year else ""),
                ", ".join(esc(a) for a in p.authors),
                esc(p.note.strip() if p.note else ""),
            ]
            for p in provenance.precursors
        ]
        parts.append("<h3>Precursors</h3>" + table(["work", "authors", "relationship"], rows))

    if provenance.attribution_notes:
        parts.append(
            "<h3>Attribution notes</h3>"
            f"<p>{esc(provenance.attribution_notes.strip())}</p>"
        )

    return "".join(parts)


def credits_section(spec: AlgorithmSpec, links: Links) -> str:
    """Who built this entry -- distinct from who created the algorithm."""
    credits = spec.credits
    if not credits.everyone():
        return ""

    def _names(ids: list[str]) -> str:
        return ", ".join(
            f'<a href="{esc(links.to_person(i))}">{esc(people.get_person(i).name)}</a>'
            if people.exists(i)
            else esc(i)
            for i in ids
        )

    rows = [
        [label, _names(ids)]
        for label, ids in [
            ("steward", credits.stewards),
            ("specification", credits.spec_curators),
            ("reference implementation", credits.reference_implementation),
            ("verifier", credits.verifier_authors),
            ("dataset curation", credits.dataset_curators),
            ("review", credits.reviewers),
        ]
        if ids
    ]
    rows.extend(
        [f"{engine} adapter", _names(ids)]
        for engine, ids in sorted(credits.adapter_contributors.items())
        if ids
    )
    return f"""<h2>Gigi contributors</h2>
<p class="lede">Who built and checked this entry. Distinct from the original
authors above: creating an algorithm, implementing it, verifying it and finding
a divergence in it are four different contributions.</p>
{table(["role", "people"], rows)}"""
