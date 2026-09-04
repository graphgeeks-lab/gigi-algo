"""Commands that answer "what do we know?".

They read the registry and print it. None of them runs a graph algorithm --
that is `execution.py`. The split mirrors the architecture: the registry is
what we claim, the harness is what happened when we checked.
"""

from __future__ import annotations

import typer
from rich.table import Table

from gigi import registry
from gigi.cli.app import app, console
from gigi.graph import list_datasets, load_graph

@app.command("list")
def list_command() -> None:
    """List the algorithms in the registry."""
    table = Table("id", "family", "maturity", "engines", "divergences")
    for algorithm_id in registry.list_algorithms():
        spec = registry.load_algorithm(algorithm_id)
        table.add_row(
            spec.id,
            spec.family,
            spec.maturity.value,
            ", ".join(registry.implemented_engines(spec.id)),
            str(len(spec.divergences)),
        )
    console.print(table)


@app.command()
def show(algorithm: str) -> None:
    """Show what the registry claims about one algorithm."""
    spec = registry.load_algorithm(algorithm)
    console.print(f"[bold]{spec.name}[/bold]  ({spec.id}, {spec.maturity.value})")
    console.print(spec.problem.strip())
    console.print()

    params = Table("parameter", "type", "gigi default", "meaning", show_lines=False)
    for parameter in spec.parameters:
        params.add_row(
            parameter.name,
            parameter.type,
            "engine default" if parameter.common_default is None else str(parameter.common_default),
            parameter.description.strip().split("\n")[0],
        )
    console.print(params)

    if spec.divergences:
        console.print()
        divergences = Table("id", "severity", "engines", "summary")
        for divergence in spec.divergences:
            divergences.add_row(
                divergence.id,
                divergence.severity.value,
                ", ".join(divergence.engines),
                divergence.summary.strip(),
            )
        console.print(divergences)


@app.command("review")
def review_command(algorithm: str) -> None:
    """What to look at before merging this algorithm.

    Separates what a machine already settled from what only a person can.
    """
    from gigi.review import review

    result = review(algorithm)
    spec = registry.load_algorithm(algorithm)

    console.print(
        f"[bold]Reviewing {spec.name}[/bold]  ({algorithm}, claims [bold]{result.maturity}[/bold])"
    )
    console.print()

    console.print(
        f"[bold]Settled by machine[/bold] -- the requirements of `{result.maturity}`, "
        "plus what happened when it ran"
    )
    table = Table("check", "", "detail")
    for check in result.checks:
        mark = "[green]pass[/green]" if check.passed else "[red]FAIL[/red]"
        table.add_row(check.name, mark, check.detail)
    console.print(table)

    target, lacking = result.promotion
    if target:
        console.print()
        if lacking:
            console.print(f"[bold]To reach `{target}`[/bold] -- what promotion would take")
            for item in lacking:
                console.print(f"  [yellow]-[/yellow] {item}")
        else:
            console.print(f"[green]Meets every requirement of `{target}`[/green] -- ready to promote")

    if result.gaps:
        console.print()
        console.print("[bold]Gaps[/bold] -- not failures, usually the next contribution")
        for gap in result.gaps:
            console.print(f"  [yellow]-[/yellow] {gap}")

    console.print()
    console.print("[bold]By eye[/bold] -- nothing checks these but you")
    for index, item in enumerate(result.by_eye, 1):
        console.print(f"  [bold]{index}. {item.question}[/bold]")
        console.print(f"     look at: {item.where}")
        console.print(f"     [dim]{item.why}[/dim]")

    if spec.maths.definition:
        console.print()
        console.print("[bold]The definition, for item 1[/bold]")
        console.print(spec.maths.definition.statement.rstrip())

    if not result.ok:
        raise typer.Exit(1)


@app.command()
def version(
    as_json: bool = typer.Option(False, "--json", help="Machine-readable."),
) -> None:
    """Which gigi, which engines, and which registry it is reading.

    The registry path matters more than it looks: an installed wheel carries
    its own copy of the content, so this is how you tell whether you are
    looking at your checkout or at the packaged one.
    """
    import json
    import platform
    import sys

    from gigi import __version__, people
    from gigi.adapters import ENGINES, engine_versions
    from gigi.graph import list_datasets
    from gigi.paths import repo_root

    root = repo_root()
    packaged = root.name == "_content"
    algorithms = registry.list_algorithms()
    divergences = sum(len(registry.load_algorithm(a).divergences) for a in algorithms)
    installed = engine_versions()

    if as_json:
        print(json.dumps({
            "gigi": __version__,
            "python": platform.python_version(),
            "platform": sys.platform,
            "registry": {"path": str(root), "packaged": packaged},
            "counts": {
                "algorithms": len(algorithms), "datasets": len(list_datasets()),
                "families": len(registry.list_families()),
                "people": len(people.list_people()), "divergences": divergences,
            },
            "engines": {name: installed.get(name) for name in ENGINES},
        }, indent=2))
        return

    console.print(f"[bold]gigi-algo {__version__}[/bold]")
    console.print(f"Python {platform.python_version()} on {sys.platform}")
    console.print()
    console.print(f"registry  {root}")
    console.print(f"          {'packaged with the wheel' if packaged else 'a checkout'}")
    console.print(
        f"          {len(algorithms)} algorithms, {len(list_datasets())} datasets, "
        f"{len(registry.list_families())} families, {len(people.list_people())} people, "
        f"{divergences} divergences"
    )
    console.print()
    engines_table = Table("engine", "version")
    for name in ENGINES:
        engines_table.add_row(name, installed.get(name) or "[dim]not installed[/dim]")
    console.print(engines_table)


@app.command()
def promote(
    algorithm: str,
    to: str = typer.Option(None, "--to", help="Target tier. Defaults to the next rung up."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Check without editing anything."),
) -> None:
    """Move an algorithm up the maturity ladder, if it has earned it.

    Checks every requirement of the target tier and refuses if any is unmet.
    Passing is necessary, not sufficient: promotion is still a person's
    decision, and this command exists so that decision is made on top of the
    checks rather than instead of them.
    """
    from gigi import requirements
    from gigi.models import Maturity

    spec = registry.load_algorithm(algorithm)
    if to:
        try:
            target = Maturity(to)
        except ValueError:
            raise typer.BadParameter(f"unknown tier {to!r}") from None
    else:
        nxt, _ = requirements.next_tier(spec)
        if nxt is None:
            console.print(f"{algorithm} is already `{spec.maturity.value}`. Nothing above it.")
            raise typer.Exit(0)
        target = nxt

    if requirements.RANK[target] <= requirements.RANK[spec.maturity] and target is not Maturity.historical:
        console.print(
            f"[red]{algorithm} is `{spec.maturity.value}`; `{target.value}` is not above it.[/red] "
            "Demotion is a deliberate hand edit, not a command."
        )
        raise typer.Exit(1)

    lacking = [
        o for o in requirements.check(spec)
        if not o.met and requirements.RANK[o.requirement.mandatory_from] <= requirements.RANK[target]
    ]
    if lacking:
        console.print(f"[red]{algorithm} is not ready for `{target.value}`.[/red] It still lacks:")
        for outcome in lacking:
            console.print(f"  [red]-[/red] {outcome.requirement.description}: {outcome.detail}")
        raise typer.Exit(1)

    console.print(f"[green]{algorithm} meets every requirement of `{target.value}`.[/green]")
    if dry_run:
        console.print("[dim]--dry-run: nothing was changed.[/dim]")
        raise typer.Exit(0)

    path = registry.set_maturity(algorithm, target)
    console.print(f"{spec.maturity.value} -> {target.value} in {path}")
    console.print()
    console.print("[bold]Still to do, by a person:[/bold]")
    console.print("  - add a line to CHANGELOG.md saying what promotion means for a user")
    console.print("  - have someone who did not write the entry read it (docs/REVIEWING.md)")
    console.print("  - commit the change to algorithm.yaml")


@app.command()
def maths(algorithm: str) -> None:
    """The mathematics: definition, invariants, and where the definition leaves
    a choice open."""
    spec = registry.load_algorithm(algorithm)
    block = spec.maths

    console.print(f"[bold]{spec.name}[/bold]")
    if block.summary:
        console.print(block.summary.strip())

    for formula in filter(None, [block.definition, *block.also]):
        console.print()
        console.print(formula.statement.rstrip())
        if formula.latex:
            console.print(f"[dim]LaTeX:[/dim] {formula.latex.strip()}")
        if formula.note:
            console.print(f"[dim]{formula.note.strip()}[/dim]")

    if block.invariants:
        console.print("\n[bold]Invariants[/bold]")
        table = Table("id", "statement", "checked")
        for invariant in block.invariants:
            table.add_row(invariant.id, invariant.statement, "yes" if invariant.check else "no")
        console.print(table)

    if block.under_determined:
        console.print("\n[bold]Where the definition leaves a choice[/bold]")
        for choice in block.under_determined:
            console.print(f"  [bold]{choice.question}[/bold]")
            for option in choice.choices:
                console.print(f"    - {option}")
            if choice.divergences:
                console.print(f"    [red]engines differ:[/red] {', '.join(choice.divergences)}")
            elif choice.datasets:
                console.print(
                    f"    [green]engines agree[/green] on {', '.join(choice.datasets)}"
                )


@app.command()
def families() -> None:
    """The algorithm taxonomy. A family is a question, not a label."""
    table = Table("family", "the question it answers", "within", "algorithms")
    for family in registry.list_families():
        table.add_row(
            family.id,
            family.question,
            registry.load_family(family.parent).name if family.parent else "",
            ", ".join(registry.algorithms_in_family(family.id)),
        )
    console.print(table)


@app.command()
def family(family_id: str) -> None:
    """One family: what it is for, what is in it, and what it borders on."""
    record = registry.load_family(family_id)
    lineage = " -> ".join(f.name for f in registry.family_lineage(family_id))

    console.print(f"[bold]{record.name}[/bold]  ({lineage})")
    console.print(f"[bold]{record.question}[/bold]")
    console.print(record.summary.strip())

    members = registry.algorithms_in_family(family_id)
    console.print(f"\nalgorithms: {', '.join(members) or 'none yet'}")
    if record.related:
        console.print(f"related families: {', '.join(record.related)}")
    if record.stewards:
        console.print(f"stewards: {', '.join(record.stewards)}")


@app.command()
def export(
    output: str = typer.Option(None, "--output", "-o", help="Write here instead of stdout."),
) -> None:
    """Dump the whole registry as one JSON document.

    The affordance for anything that is not a person: an agent, another tool, a
    static site generator. Everything the registry knows -- algorithms, their
    maths and invariants, families, relationships, provenance, credits,
    divergences and people -- serialised from the same models the library uses,
    so it cannot drift from what `gigi verify` actually checks.
    """
    import json

    from gigi import __version__, people

    document = {
        "gigi_version": __version__,
        "families": [f.model_dump(mode="json") for f in registry.list_families()],
        "people": [p.model_dump(mode="json") for p in people.list_people()],
        "algorithms": [
            registry.load_algorithm(a).model_dump(mode="json", by_alias=True)
            for a in registry.list_algorithms()
        ],
        "datasets": [
            load_graph(d).metadata.model_dump(mode="json") for d in list_datasets()
        ],
    }
    text = json.dumps(document, indent=2, ensure_ascii=False)

    if output:
        from pathlib import Path

        Path(output).write_text(text, encoding="utf-8")
        console.print(f"wrote {output}")
    else:
        print(text)


@app.command()
def origin(algorithm: str) -> None:
    """Where an algorithm came from, and who built the entry for it.

    Two different questions, shown separately on purpose.
    """
    from gigi import people

    spec = registry.load_algorithm(algorithm)
    provenance = spec.provenance

    console.print(f"[bold]{spec.name}[/bold]")
    if provenance.introduced:
        console.print(f"introduced {provenance.introduced}")

    if provenance.original_authors:
        console.print("\n[bold]Original authors[/bold]")
        for author in provenance.original_authors:
            suffix = f"  ({author.note.strip().splitlines()[0]})" if author.note else ""
            console.print(f"  {author.name}{suffix}")

    if provenance.original_work:
        work = provenance.original_work
        console.print("\n[bold]Original work[/bold]")
        console.print(f"  {work.title}")
        detail = ", ".join(str(b) for b in (work.venue, work.year, work.doi, work.url) if b)
        if detail:
            console.print(f"  {detail}")

    if provenance.precursors:
        console.print("\n[bold]Precursors[/bold]")
        for precursor in provenance.precursors:
            year = f" ({precursor.year})" if precursor.year else ""
            authors = f" -- {', '.join(precursor.authors)}" if precursor.authors else ""
            console.print(f"  {precursor.name}{year}{authors}")

    if provenance.attribution_notes:
        console.print("\n[bold]Attribution notes[/bold]")
        console.print(f"  {provenance.attribution_notes.strip()}")

    if spec.credits.everyone():
        console.print("\n[bold]Gigi contributors[/bold]")
        table = Table("role", "people")
        pairs = [
            ("steward", spec.credits.stewards),
            ("specification", spec.credits.spec_curators),
            ("reference implementation", spec.credits.reference_implementation),
            ("verifier", spec.credits.verifier_authors),
            ("dataset curation", spec.credits.dataset_curators),
            ("review", spec.credits.reviewers),
        ]
        pairs.extend(
            (f"{engine} adapter", ids)
            for engine, ids in sorted(spec.credits.adapter_contributors.items())
        )
        for label, ids in pairs:
            if ids:
                table.add_row(
                    label,
                    ", ".join(
                        people.get_person(i).name if people.exists(i) else i for i in ids
                    ),
                )
        console.print(table)


@app.command("people")
def people_command() -> None:
    """Who has contributed, and to what."""
    from gigi import people

    # Roles live on `gigi person`; this table is for scanning who works on what.
    table = Table("id", "name", "algorithms", "divergences found")
    for person in people.list_people():
        profile = people.profile(person.id)
        table.add_row(
            person.id,
            person.name,
            ", ".join(profile.algorithms),
            str(len(profile.discoveries)),
        )
    console.print(table)


@app.command()
def person(person_id: str) -> None:
    """One contributor's lineage. Deliberately not a score."""
    from gigi import people

    profile = people.profile(person_id)
    console.print(f"[bold]{profile.person.name}[/bold]  ({profile.person.id})")
    if profile.person.roles:
        console.print(", ".join(role.value for role in profile.person.roles))

    contributions = Table("algorithm", "contribution", "detail")
    for contribution in profile.contributions:
        contributions.add_row(contribution.algorithm_id, contribution.role, contribution.detail)
    console.print(contributions)

    if profile.discoveries:
        console.print("\n[bold]Divergences found[/bold]")
        for discovery in profile.discoveries:
            console.print(f"  {discovery.algorithm_id}: {discovery.detail}")
