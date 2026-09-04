"""Commands that answer "what does this mean, and is it right for me?".

`knowledge.py` prints what the registry holds. These four interpret it: what a
method answers and does not, what else would do the job, where it sits, and --
the one that needs the user's own data -- whether it will read their columns
the way they mean them.
"""

from __future__ import annotations

import typer
from rich.table import Table

from gigi import registry
from gigi.cli.app import app, console
from gigi.data import load_dataset
from gigi.graph import GraphData

@app.command()
def why(
    method: str,
    dataset: str = typer.Option(
        None, "--dataset", "-d", "--graph", "-g",
        help="Check the method's assumptions against real data.",
    ),
) -> None:
    """What this method answers, what it does not, and how it reads its input.

    Without --dataset this is documentation. With it, it is advice: the same
    output plus what the method will make of the data actually in front of you.
    """
    from gigi import semantics

    spec = registry.load_method(method)
    console.print(f"[bold]{spec.name}[/bold]")
    console.print(spec.summary.strip())

    if spec.problems:
        console.print("\n[bold]Answers[/bold]")
        for problem_id in spec.problems:
            problem = registry.load_problem(problem_id)
            console.print(f"  {problem.question.strip()}")
            console.print(f"  [dim]{problem_id}[/dim]")

    if spec.intent.not_for:
        console.print("\n[bold]Does not answer[/bold]")
        for problem_id in spec.intent.not_for:
            problem = registry.load_problem(problem_id)
            solvers = registry.methods_for_problem(problem_id)
            hint = f"  [dim]-> {', '.join(solvers)}[/dim]" if solvers else "  [dim]-> nothing here yet[/dim]"
            console.print(f"  {problem.question.strip()}{hint}")

    for interpretation in spec.semantic_interpretations:
        console.print(f"\n[bold]How it reads {interpretation.subject.replace('_', ' ')}[/bold]")
        if interpretation.higher_means:
            console.print(
                f"  as [bold]{interpretation.semantic_role}[/bold]: "
                f"higher means {interpretation.higher_means}"
            )
        console.print(f"  {interpretation.description.strip()}")

    if not dataset:
        console.print(
            "\n[dim]Pass --dataset <id> to check these assumptions against your data.[/dim]"
        )
        return

    data = load_dataset(dataset)
    console.print(f"\n[bold]Your data[/bold]  ({data.id})")

    # The column-meaning check reads column names, so it has something to say
    # about a graph and nothing to say about vectors. Saying so is better than
    # printing "nothing to flag", which would read as a clean bill of health.
    if isinstance(data, GraphData):
        findings = semantics.check_graph(spec, data)
        if not findings:
            console.print("  [green]nothing to flag[/green]")
        for finding in findings:
            mark = "[red]![/red]" if finding.serious else "[yellow]-[/yellow]"
            console.print(f"  {mark} {finding.question()}")
            if finding.note:
                console.print(f"    [dim]{finding.note.strip()}[/dim]")
    else:
        console.print(
            "  [dim]no column-meaning check for this kind of data yet; the "
            "vocabulary reads column names.[/dim]"
        )

    applicable = semantics.divergences_for_dataset(spec, data.id)
    for divergence_id in applicable:
        divergence = spec.divergence(divergence_id)
        console.print(f"  [red]![/red] {divergence_id} is reproduced on this exact fixture.")
        console.print(f"    [dim]{divergence.summary.strip()}[/dim]")

    others = len(spec.divergences) - len(applicable)
    if others > 0:
        console.print(
            f"  [dim]{others} more declared divergence(s) for this method: gigi show {method}[/dim]"
        )


@app.command()
def alternatives(method: str) -> None:
    """Other methods for the same job, and when each is the right one."""
    spec = registry.load_method(method)
    known = set(registry.list_methods())

    shown = 0
    for relationship in spec.relationships:
        if relationship.kind.value != "alternative_to":
            continue
        target = relationship.method
        shown += 1

        if target in known:
            other = registry.load_method(target)
            headline = (
                registry.load_problem(other.problems[0]).question.strip()
                if other.problems
                else registry.load_family(other.family).question
            )
            console.print()
            console.print(f"[bold]{other.name}[/bold]  [dim]{target}[/dim]")
        else:
            headline = ""
            console.print()
            console.print(f"[bold]{target}[/bold]  [dim]not in the registry yet[/dim]")

        if headline:
            console.print(f"  Use it when: {headline}")
        if relationship.note:
            console.print(f"  {relationship.note.strip()}")
        if relationship.condition:
            console.print(f"  [dim]Coincides when: {relationship.condition.strip()}[/dim]")

    if not shown:
        console.print(f"{method} declares no alternatives.")


@app.command()
def related(method: str) -> None:
    """Where this method sits: its problems, family, neighbours and backends."""
    spec = registry.load_method(method)
    known = set(registry.list_methods())
    family = registry.load_family(spec.family)

    console.print(f"[bold]{spec.name}[/bold]")
    console.print(f"{registry.domain_of(spec)} / {family.name} -- {family.question}")

    if spec.problems:
        console.print("\n[bold]Solves[/bold]")
        for problem_id in spec.problems:
            problem = registry.load_problem(problem_id)
            others = [m for m in registry.methods_for_problem(problem_id) if m != method]
            also = f"  [dim](also: {', '.join(others)})[/dim]" if others else ""
            console.print(f"  {problem.name}: {problem.question.strip()}{also}")

    by_kind: dict[str, list[str]] = {}
    for relationship in spec.relationships:
        label = relationship.method
        if relationship.method not in known:
            label += " [dim](not here yet)[/dim]"
        by_kind.setdefault(relationship.kind.value.replace("_", " "), []).append(label)
    for kind, targets in sorted(by_kind.items()):
        console.print(f"\n[bold]{kind.capitalize()}[/bold]")
        for target in targets:
            console.print(f"  {target}")

    siblings = [m for m in registry.methods_in_family(spec.family) if m != method]
    if siblings:
        console.print(f"\n[bold]Same family[/bold]\n  {', '.join(siblings)}")

    console.print(f"\n[bold]Implemented on[/bold]\n  {', '.join(registry.implemented_backends(method))}")

    if spec.use_cases:
        console.print("\n[bold]Used for[/bold]")
        for use_case in spec.use_cases:
            console.print(f"  {use_case.question.strip()}  [dim]({use_case.domain})[/dim]")


@app.command()
def problems() -> None:
    """The questions the registry knows about, and what answers them."""
    table = Table("problem", "domain", "question", "solved by")
    for problem in registry.list_problems():
        solvers = registry.methods_for_problem(problem.id)
        table.add_row(
            problem.id,
            problem.domain,
            problem.question.strip(),
            ", ".join(solvers) or "[dim]nothing yet[/dim]",
        )
    console.print(table)


@app.command()
def problem(problem_id: str) -> None:
    """One problem: the question, and every method that claims to answer it."""
    spec = registry.load_problem(problem_id)
    console.print(f"[bold]{spec.name}[/bold]  ({spec.domain})")
    console.print(f"[bold]{spec.question.strip()}[/bold]")
    if spec.description:
        console.print(f"\n{spec.description.strip()}")

    solvers = registry.methods_for_problem(problem_id)
    console.print(f"\n[bold]Solved by[/bold]\n  {', '.join(solvers) or 'nothing in the registry yet'}")

    mistaken = [
        m for m in registry.list_methods() if problem_id in registry.load_method(m).intent.not_for
    ]
    if mistaken:
        console.print(f"\n[bold]Commonly mistaken for[/bold]\n  {', '.join(mistaken)}")

    if spec.related_problems:
        console.print(f"\n[bold]Related questions[/bold]\n  {', '.join(spec.related_problems)}")


