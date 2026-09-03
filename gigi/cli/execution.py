"""Commands that answer "what happened when we ran it?".

Every one of these is a few lines of formatting around `gigi.harness`. If a
command here ever needs logic of its own, that logic belongs in the library --
the CLI, the Python API and any future agent tool must not drift apart.
"""

from __future__ import annotations

import typer
from rich.table import Table

from gigi import registry, runstore
from gigi.adapters import available_engines, engine_versions
from gigi.cli.app import app, console, parse_overrides
from gigi.graph import list_datasets, load_graph, profile_graph
from gigi.harness import compare as compare_engines
from gigi.harness import run as run_algorithm
from gigi.harness import runnable_engines
from gigi.harness import verify as verify_algorithm
from gigi.models import RunStatus

@app.command()
def engines() -> None:
    """Show which engines are installed here."""
    table = Table("engine", "installed", "version")
    for name, version in engine_versions().items():
        table.add_row(name, "yes", version or "unknown")
    for name in ("reference", "networkx", "igraph", "rustworkx"):
        if name not in engine_versions():
            table.add_row(name, "no", "-")
    console.print(table)


@app.command()
def datasets() -> None:
    """List the graph fixtures."""
    table = Table("id", "nodes", "edges", "features")
    for dataset_id in list_datasets():
        graph = load_graph(dataset_id)
        profile = profile_graph(graph)
        features = [name for name, on in graph.metadata.features.items() if on]
        table.add_row(
            dataset_id, str(profile.node_count), str(profile.edge_count), ", ".join(features)
        )
    console.print(table)


@app.command()
def inspect(graph: str) -> None:
    """Profile a graph. Cheap facts only: nothing here is a graph algorithm."""
    profile = profile_graph(load_graph(graph))
    table = Table("property", "value")
    for name, value in profile.model_dump().items():
        table.add_row(name, str(value))
    console.print(table)


@app.command()
def run(
    algorithm: str,
    graph: str = typer.Option(..., "--graph", "-g", help="Dataset id or directory."),
    engine: str = typer.Option("reference", "--engine", "-e"),
    set_: list[str] = typer.Option(None, "--set", "-s", help="Parameter override, name=value."),
    explicit: bool = typer.Option(
        False, "--explicit", help="Pin ambiguous parameters instead of using engine defaults."
    ),
) -> None:
    """Run one algorithm on one engine."""
    from gigi.harness import resolve_parameters

    spec = registry.load_algorithm(algorithm)
    data = load_graph(graph)
    params = resolve_parameters(spec, data, parse_overrides(set_), explicit=explicit)

    result = run_algorithm(spec, engine, data, params)
    runstore.save_run(result)

    if result.status != RunStatus.ok:
        console.print(f"[red]{result.status.value}[/red]: {result.error}")
        raise typer.Exit(1)

    console.print(
        f"[bold]{spec.id}[/bold] on [bold]{engine} {result.engine_version}[/bold] "
        f"over [bold]{data.id}[/bold]  ({result.total_duration_ms:.1f} ms)"
    )

    params_table = Table("requested", "value", "effective", "value")
    requested = list(result.requested_parameters.items())
    effective = list(result.effective_parameters.items())
    for index in range(max(len(requested), len(effective))):
        left = requested[index] if index < len(requested) else ("", "")
        right = effective[index] if index < len(effective) else ("", "")
        params_table.add_row(str(left[0]), str(left[1]), str(right[0]), str(right[1]))
    console.print(params_table)

    scores = Table("node", spec.output.score_name or "score")
    ranked = sorted(result.result.scores.items(), key=lambda kv: -kv[1])
    for node, score in ranked:
        scores.add_row(node, f"{score:.8f}")
    console.print(scores)


@app.command()
def compare(
    algorithm: str,
    graph: str = typer.Option(..., "--graph", "-g"),
    engines_option: str = typer.Option(None, "--engines", help="Comma-separated engine list."),
    set_: list[str] = typer.Option(None, "--set", "-s"),
    defaults: bool = typer.Option(
        False, "--defaults", help="Use each engine's own defaults instead of pinning parameters."
    ),
) -> None:
    """Run every engine on one graph and compare them against the reference."""
    spec = registry.load_algorithm(algorithm)
    selected = engines_option.split(",") if engines_option else None
    runs, comparisons = compare_engines(
        spec,
        graph,
        engines=selected,
        parameters=parse_overrides(set_),
        explicit=not defaults,
    )

    table = Table("engine", "version", "status", "ms", "top node", "max abs error", "agrees")
    metrics = {c.engine_b: c for c in comparisons}
    for result in runs:
        comparison = metrics.get(result.engine)
        top = (
            max(result.result.scores, key=lambda n: result.result.scores[n])
            if result.result
            else "-"
        )
        table.add_row(
            result.engine,
            result.engine_version or "-",
            result.status.value,
            f"{result.total_duration_ms:.1f}",
            top,
            "baseline" if comparison is None else f"{comparison.metrics.get('max_abs_error', 0):.3e}",
            "-" if comparison is None else ("yes" if comparison.equivalent else "[red]NO[/red]"),
        )
    console.print(table)


@app.command()
def verify(
    algorithm: str = typer.Argument(None, help="Algorithm id; omit to verify all."),
    save: bool = typer.Option(True, "--save/--no-save", help="Write the report to .gigi/reports."),
) -> None:
    """Check the registry's claims against reality."""
    targets = [algorithm] if algorithm else registry.list_algorithms()
    failed = False

    for algorithm_id in targets:
        spec = registry.load_algorithm(algorithm_id)
        report = verify_algorithm(spec)
        if save:
            runstore.save_report(report)

        colour = "green" if report.status == "pass" else "red"
        console.print(
            f"[{colour}]{report.status.upper()}[/{colour}] {algorithm_id} "
            f"-- {report.conclusion}"
        )

        if report.divergence_checks:
            table = Table("divergence", "dataset", "engines", "expected", "observed", "ok")
            for check in report.divergence_checks:
                table.add_row(
                    check.divergence_id,
                    ", ".join(check.datasets),
                    " vs ".join(check.engines),
                    check.expected,
                    check.observed,
                    "yes" if check.reproduced else ("skip" if check.observed == "skipped" else "[red]NO[/red]"),
                )
            console.print(table)

        for difference in report.undeclared_differences:
            console.print(
                f"  [red]undeclared[/red] {difference.engine_a} vs {difference.engine_b} "
                f"on {difference.dataset_id}: max abs error "
                f"{difference.metrics.get('max_abs_error', float('nan')):.3e}"
            )
        for difference in report.explained_differences:
            console.print(
                f"  [yellow]explained[/yellow] by {difference.divergence_id}: "
                f"{difference.engine_a} vs {difference.engine_b} on {difference.dataset_id}"
            )

        failed = failed or report.status == "fail"

    if failed:
        raise typer.Exit(1)


site_app = typer.Typer(help="Generate the static site.", no_args_is_help=True)
app.add_typer(site_app, name="site")


@site_app.command("build")
def site_build(
    output: str = typer.Option("site", "--output", "-o"),
    verify_first: bool = typer.Option(
        True, "--verify/--no-verify", help="Run verification so the site shows live evidence."
    ),
    single_file: bool = typer.Option(
        False, "--single-file", help="Emit one self-contained HTML document instead of a site."
    ),
) -> None:
    """Render the registry, and the latest verification evidence, as static HTML."""
    from gigi.site import build_site

    path = build_site(output, verify_first=verify_first, single_file=single_file)
    console.print(f"wrote {path}")


@app.command()
def status() -> None:
    """What is installed and what is verifiable in this environment."""
    console.print(f"engines available: {', '.join(available_engines())}")
    for algorithm_id in registry.list_algorithms():
        spec = registry.load_algorithm(algorithm_id)
        console.print(f"  {algorithm_id}: runnable on {', '.join(runnable_engines(spec))}")
