"""Commands for when the caller is not a person.

    ask     a question, answered from the registry and nothing else
    tools   the tool manifest, for any runtime that takes JSON schemas
    mcp     the same tools, served over MCP on stdio

`ask` will use a model to *find* the right registry entries, and never to say
anything. A model picks ids from a catalogue; every id is validated against the
registry; the words a user reads all come from the registry itself. Where no
model is configured, token matching runs instead and the output is identical in
shape -- see docs/adr/0014-a-model-may-find-but-not-speak.md.

Every answer says which path matched it, because whether a model was involved
in choosing is not something a user should have to guess.

To get a *generated* answer, give the grounded context to a model that can also
call the tools -- `gigi ask --format context` is written for that, and the MCP
server is the better version of it.
"""

from __future__ import annotations

import json
import os

import typer

from rich.table import Table

from gigi import registry
from gigi.ask import ask as ask_registry
from gigi.agent.manifest import FORMATS, manifest
from gigi.cli.app import app, console


@app.command()
def ask(
    question: str = typer.Argument(..., help="A question, in plain language."),
    output: str = typer.Option(
        "text", "--format", "-f", help="text, json, or context (grounded prompt material)."
    ),
    limit: int = typer.Option(6, "--limit", "-n", help="How many matches to consider."),
    model: str = typer.Option(
        None, "--model", "-m",
        help="auto (default), none, or a provider: anthropic, openai, ollama. "
             "A model chooses which entries match; it never writes the answer.",
    ),
) -> None:
    """Ask the registry a question. Answers only from what is verified here.

    A configured model is used to *find* the right entries -- it reads
    paraphrase, which word matching cannot. It selects registry ids and nothing
    else; every word printed comes from the registry. `--model none` forces
    word matching, and `GIGI_MODEL` sets the default.

    Where nothing in the registry answers the question it says so rather than
    offering the nearest thing, which is the whole point.
    """
    answer = ask_registry(question, limit=limit, provider=_provider(model))

    if output == "json":
        from gigi.agent.tools import call

        console.print_json(json.dumps(call("gigi_ask", {"question": question})))
        return
    if output == "context":
        console.print(_context(answer))
        return

    console.print(f"[bold]{question}[/bold]")
    # Never invisible: a user is entitled to know whether a model chose these
    # without having to ask, and to see when it silently fell back.
    how = "word matching" if answer.matched_by == "keywords" else f"{answer.matched_by} (model)"
    console.print(f"[dim]matched by {how}[/dim]\n")

    if answer.found_nothing:
        console.print("[yellow]Nothing in the registry matches this question.[/yellow]")
        console.print(
            "\n[dim]That is an answer, not a failure. Gigi holds "
            f"{len(registry.list_methods())} verified methods; anything else would "
            "be a guess, and a guess from here would look exactly like a checked "
            "claim.[/dim]"
        )
        return

    if answer.answered_by:
        console.print("[bold]Answered by[/bold]")
        for method_id in answer.answered_by:
            spec = registry.load_method(method_id)
            console.print(f"  [green]{method_id}[/green] -- {spec.summary.strip()}")
            console.print(f"    [dim]{spec.maturity.value}; gigi why {method_id}[/dim]")
    elif answer.problems:
        console.print("[yellow]Nothing here answers this.[/yellow]")
        for problem_id in answer.problems:
            problem = registry.load_problem(problem_id)
            console.print(f"  the question is known: [bold]{problem.question.strip()}[/bold]")
            console.print(f"  [dim]problems/{problem_id}.yaml -- no method claims it[/dim]")

    if answer.not_answered_by:
        console.print("\n[bold]Explicitly not for this[/bold]")
        for problem_id, method_id in answer.not_answered_by:
            console.print(f"  [red]{method_id}[/red] declares {problem_id} out of scope")

    # Weak matches, minus anything already named above -- repeating a
    # recommendation under 'less confidently' undercuts it.
    shown = set(answer.answered_by) | set(answer.problems)
    related = [m for m in answer.matches if m not in answer.confident and m.id not in shown]
    if related:
        console.print(
            "\n[dim]Also matched, less confidently: "
            + ", ".join(f"{m.kind} {m.id}" for m in related)
            + "[/dim]"
        )


def _provider(choice: str | None):
    """Which model to match with, if any.

    `auto` is the default because a configured key is a deliberate act, and
    because the alternative -- silently doing worse than the machine can --
    is a poor default for the one command aimed at people who do not yet know
    what to search for. `GIGI_MODEL=none` turns it off everywhere.
    """
    from gigi.providers import first_available, get_provider

    choice = (choice or os.environ.get("GIGI_MODEL") or "auto").strip().lower()
    if choice in {"none", "off", "keywords"}:
        return None
    if choice == "auto":
        return first_available()
    try:
        provider = get_provider(choice)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if not provider.available():
        raise typer.BadParameter(
            f"{choice} is not configured here. `gigi providers` shows what is."
        )
    return provider


def _context(answer) -> str:
    """The same answer as prompt material for a model elsewhere.

    Everything a model needs to answer well and nothing it could mistake for
    permission to improvise -- which is why the instruction comes first, before
    the model has read anything it might want to embellish.
    """
    lines = [
        "# Gigi registry context",
        "",
        "Answer ONLY from the facts below. Cite method ids. If the facts do not",
        "answer the question, say so -- do not fall back on general knowledge,",
        "because every claim here is verified and a claim from outside is not.",
        "",
        f"## Question\n{answer.question}",
        "",
    ]
    if answer.found_nothing:
        lines.append("## Registry\nNothing matches. There is no grounded answer to give.")
        return "\n".join(lines)

    if answer.answered_by:
        lines.append("## Methods that answer this")
        for method_id in answer.answered_by:
            spec = registry.load_method(method_id)
            lines += [
                f"### {method_id} ({spec.maturity.value})",
                spec.summary.strip(),
                f"- family: {spec.family}, domain: {registry.domain_of(spec)}",
                f"- backends: {', '.join(registry.implemented_backends(method_id))}",
                f"- recorded divergences: {len(spec.divergences)}",
            ]
            if spec.ai_context and spec.ai_context.instructions:
                lines.append(f"- guidance: {spec.ai_context.instructions.strip()}")
            lines.append("")
    elif answer.problems:
        lines += [
            "## No method answers this",
            "The question is one the registry knows, but nothing here solves it:",
        ]
        lines += [f"- {registry.load_problem(p).question.strip()} ({p})" for p in answer.problems]
        lines.append("")

    if answer.not_answered_by:
        lines.append("## Explicitly out of scope")
        lines += [f"- {m} declares {p} out of scope" for p, m in answer.not_answered_by]
    return "\n".join(lines)


@app.command()
def tools(
    output: str = typer.Option("mcp", "--format", "-f", help=f"One of: {', '.join(FORMATS)}."),
) -> None:
    """Print the agent tool manifest, for any runtime that takes JSON schemas."""
    try:
        console.print_json(json.dumps(manifest(output)))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def mcp() -> None:
    """Serve the registry to an agent over MCP, on stdio.

    Add to Claude Code or Claude Desktop:

        {"mcpServers": {"gigi": {"command": "gigi", "args": ["mcp"]}}}
    """
    from gigi.agent.mcp import serve

    serve()


@app.command()
def providers() -> None:
    """Which model providers are configured here, and how to set one up.

    A model is optional. Without one, `gigi ask` matches on words -- it works,
    it is just worse at paraphrase.
    """
    from gigi.providers import PROVIDERS

    table = Table("provider", "configured", "model", "how to enable")
    setup = {
        "anthropic": "set ANTHROPIC_API_KEY",
        "openai": "set OPENAI_API_KEY (and OPENAI_BASE_URL for a local server)",
        "ollama": "run ollama locally, or set OLLAMA_HOST",
    }
    for name, module in PROVIDERS.items():
        ready = module.available()
        table.add_row(
            name,
            "[green]yes[/green]" if ready else "no",
            module.model() if ready else "-",
            "" if ready else setup.get(name, ""),
        )
    console.print(table)
    console.print(
        "\n[dim]A model only chooses which registry entries match a question. "
        "Every word `gigi ask` prints comes from the registry, with or without "
        "one.[/dim]"
    )
