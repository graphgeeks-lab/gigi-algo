"""Commands that answer "what happened when we ran it?".

Every one of these is a few lines of formatting around `gigi.harness`. If a
command here ever needs logic of its own, that logic belongs in the library --
the CLI, the Python API and any future agent tool must not drift apart.
"""

from __future__ import annotations

import typer
from rich.table import Table

from gigi import registry, runstore
from gigi.backends import available_backends, backend_versions
from gigi.cli.app import app, console, parse_overrides
from gigi.data import describe, list_datasets, load_dataset, profile_dataset
from gigi.models import OutputKind, PartitionResult
from gigi.harness import compare as compare_engines
from gigi.harness import run as run_algorithm
from gigi.harness import runnable_backends
from gigi.harness import verify as verify_algorithm
from gigi.models import RunStatus

@app.command()
def backends() -> None:
    """Show which backends are installed here."""
    table = Table("backend", "installed", "version")
    for name, version in backend_versions().items():
        table.add_row(name, "yes", version or "unknown")
    for name in ("reference", "networkx", "igraph", "rustworkx"):
        if name not in backend_versions():
            table.add_row(name, "no", "-")
    console.print(table)


@app.command()
def datasets() -> None:
    """List the fixtures, of every kind."""
    table = Table("id", "kind", "shape", "features")
    for dataset_id in list_datasets():
        data = load_dataset(dataset_id)
        profile = profile_dataset(data)
        features = [name for name, on in data.metadata.features.items() if on]
        table.add_row(
            dataset_id, profile.kind, describe(profile), ", ".join(features)
        )
    console.print(table)


@app.command()
def inspect(dataset: str) -> None:
    """Profile a fixture. Cheap facts only: nothing here is an analysis."""
    profile = profile_dataset(load_dataset(dataset))
    table = Table("property", "value")
    for name, value in profile.model_dump().items():
        table.add_row(name, str(value))
    console.print(table)


@app.command()
def run(
    algorithm: str,
    dataset: str = typer.Option(
        ..., "--dataset", "-d", "--graph", "-g",
        help="Dataset id or directory, of any kind.",
    ),
    backend: str = typer.Option("reference", "--backend", "-e"),
    set_: list[str] = typer.Option(None, "--set", "-s", help="Parameter override, name=value."),
    explicit: bool = typer.Option(
        False, "--explicit", help="Pin ambiguous parameters instead of using backend defaults."
    ),
    allow_frontier: bool = typer.Option(
        False, "--allow-frontier", help="Run a `frontier` algorithm. See docs/MATURITY.md."
    ),
) -> None:
    """Run one algorithm on one backend."""
    from gigi.harness import resolve_parameters

    spec = registry.load_method(algorithm)
    data = load_dataset(dataset)
    params = resolve_parameters(spec, data, parse_overrides(set_), explicit=explicit)

    result = run_algorithm(spec, backend, data, params, allow_frontier=allow_frontier)
    runstore.save_run(result)

    if result.status != RunStatus.ok:
        console.print(f"[red]{result.status.value}[/red]: {result.error}")
        raise typer.Exit(1)

    console.print(
        f"[bold]{spec.id}[/bold] on [bold]{backend} {result.backend_version}[/bold] "
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

    console.print(_result_table(spec, result.result))


# What the key means differs by output kind, and so does what is worth showing:
# a ranking for scores, the groups themselves for a partition. Naming the column
# correctly is most of the job -- a column headed "node" over a list of pair ids
# is worse than no header.
KEY_LABELS = {"similarity_score": "pair", "node_score": "node"}


def _result_table(spec, result) -> Table:
    """One result, rendered as whatever it actually is."""
    if isinstance(result, PartitionResult):
        table = Table(spec.output.label_name or "component", "size", "members")
        groups = sorted(result.groups(), key=lambda g: (-len(g), sorted(g)))
        for members in groups:
            ordered = sorted(members, key=lambda k: result.assignments[k])
            label = result.assignments[next(iter(ordered))]
            table.add_row(label, str(len(members)), ", ".join(sorted(members)))
        return table

    table = Table(KEY_LABELS.get(result.kind.value, "key"), spec.output.score_name or "score")
    for key, score in sorted(result.scores.items(), key=lambda kv: -kv[1]):
        table.add_row(key, f"{score:.8f}")
    return table


def _headline(result) -> str:
    """The one-line summary of a result, for the comparison table.

    For scores that is the top-ranked key. For a partition there is no ranking,
    so it is the shape: how many groups, and how big the largest is.
    """
    if result is None:
        return "-"
    if isinstance(result, PartitionResult):
        sizes = result.sizes()
        groups = "group" if len(sizes) == 1 else "groups"
        return f"{len(sizes)} {groups}, largest {sizes[0] if sizes else 0}"
    return max(result.scores, key=lambda k: result.scores[k]) if result.scores else "-"


@app.command()
def compare(
    algorithm: str,
    dataset: str = typer.Option(..., "--dataset", "-d", "--graph", "-g"),
    backends_option: str = typer.Option(None, "--backends", help="Comma-separated backend list."),
    set_: list[str] = typer.Option(None, "--set", "-s"),
    defaults: bool = typer.Option(
        False, "--defaults", help="Use each backend's own defaults instead of pinning parameters."
    ),
    allow_frontier: bool = typer.Option(False, "--allow-frontier"),
) -> None:
    """Run every backend on one fixture and compare them against the reference."""
    spec = registry.load_method(algorithm)
    selected = backends_option.split(",") if backends_option else None
    runs, comparisons = compare_engines(
        spec,
        dataset,
        backends=selected,
        parameters=parse_overrides(set_),
        explicit=not defaults,
        allow_frontier=allow_frontier,
    )

    # A partition has no "max abs error" and no top-ranked key, so the two
    # result-shaped columns are named for what each kind actually has.
    partition = spec.output.kind is OutputKind.partition
    table = Table(
        "backend",
        "version",
        "status",
        "ms",
        "shape" if partition else "top key",
        "regrouped" if partition else "max abs error",
        "agrees",
    )
    metrics = {c.backend_b: c for c in comparisons}
    for result in runs:
        comparison = metrics.get(result.backend)
        top = _headline(result.result)
        if comparison is None:
            difference = "baseline"
        elif partition:
            difference = f"{int(comparison.metrics.get('keys_grouped_differently', 0))} node(s)"
        else:
            difference = f"{comparison.metrics.get('max_abs_error', 0):.3e}"
        table.add_row(
            result.backend,
            result.backend_version or "-",
            result.status.value,
            f"{result.total_duration_ms:.1f}",
            top,
            difference,
            "-" if comparison is None else ("yes" if comparison.equivalent else "[red]NO[/red]"),
        )
    console.print(table)


@app.command()
def verify(
    algorithm: str = typer.Argument(None, help="Algorithm id; omit to verify all."),
    save: bool = typer.Option(True, "--save/--no-save", help="Write the report to .gigi/reports."),
    allow_frontier: bool = typer.Option(
        False, "--allow-frontier", help="Include `frontier` algorithms. See docs/MATURITY.md."
    ),
) -> None:
    """Check the registry's claims against reality."""
    from gigi.maturity import FrontierBlocked

    targets = [algorithm] if algorithm else registry.list_methods()
    failed = False

    for method_id in targets:
        spec = registry.load_method(method_id)
        try:
            report = verify_algorithm(spec, allow_frontier=allow_frontier)
        except FrontierBlocked as blocked:
            # Verifying everything should not stop at a frontier entry, but it
            # must not silently pretend to have checked one either.
            console.print(f"[yellow]SKIP[/yellow] {method_id} -- {blocked}")
            if algorithm:
                raise typer.Exit(1)
            continue
        if save:
            runstore.save_report(report)

        colour = "green" if report.status == "pass" else "red"
        console.print(
            f"[{colour}]{report.status.upper()}[/{colour}] {method_id} "
            f"-- {report.conclusion}"
        )

        if report.divergence_checks:
            table = Table("divergence", "dataset", "backends", "expected", "observed", "ok")
            for check in report.divergence_checks:
                table.add_row(
                    check.divergence_id,
                    ", ".join(check.datasets),
                    " vs ".join(check.backends),
                    check.expected,
                    check.observed,
                    "yes" if check.reproduced else ("skip" if check.observed == "skipped" else "[red]NO[/red]"),
                )
            console.print(table)

        for difference in report.undeclared_differences:
            console.print(
                f"  [red]undeclared[/red] {difference.backend_a} vs {difference.backend_b} "
                f"on {difference.dataset_id}: max abs error "
                f"{difference.metrics.get('max_abs_error', float('nan')):.3e}"
            )
        for difference in report.explained_differences:
            console.print(
                f"  [yellow]explained[/yellow] by {difference.divergence_id}: "
                f"{difference.backend_a} vs {difference.backend_b} on {difference.dataset_id}"
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
def typst(
    algorithm: str = typer.Argument(None, help="Algorithm id; omit for all."),
    output: str = typer.Option("site/typst", "--output", "-o"),
    pdf: bool = typer.Option(False, "--pdf", help="Also compile to PDF (needs gigi-algo[docs])."),
    verify_first: bool = typer.Option(True, "--verify/--no-verify"),
    review: bool = typer.Option(
        False, "--review", help="Add the open questions from `gigi review` as margin notes."
    ),
) -> None:
    """Typeset an entry as a Typst document, for printing, review or citation.

    Maths is rendered from the same LaTeX the spec stores, via mitex. With
    --review, the gaps become margin notes and a reviewer checklist is appended.
    """
    from gigi.typst import compile_available, write

    if pdf and not compile_available():
        console.print("[red]PDF needs the typst package:[/red] pip install 'gigi-algo[docs]'")
        raise typer.Exit(1)

    for method_id in [algorithm] if algorithm else registry.list_methods():
        for path in write(method_id, output, pdf=pdf, verify_first=verify_first, review=review):
            console.print(f"wrote {path}")


@app.command()
def status() -> None:
    """What is installed and what is verifiable in this environment."""
    from gigi.maturity import FRONTIER_ENV, frontier_allowed, gated

    console.print(f"backends available: {', '.join(available_backends())}")
    for method_id in registry.list_methods():
        spec = registry.load_method(method_id)
        note = ""
        if gated(spec):
            note = (
                "  [yellow](frontier: needs --allow-frontier)[/yellow]"
                if not frontier_allowed()
                else f"  [yellow](frontier: allowed by {FRONTIER_ENV})[/yellow]"
            )
        console.print(
            f"  {method_id}: runnable on {', '.join(runnable_backends(spec))}{note}"
        )
