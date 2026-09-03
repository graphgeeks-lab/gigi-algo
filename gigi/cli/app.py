"""The Typer application, and the two things every command needs.

Commands live in `knowledge.py` and `execution.py` and register themselves onto
this app. Kept in its own module so those two can import it without importing
each other.
"""

from __future__ import annotations

from typing import Any

import typer
import yaml
from rich.console import Console

app = typer.Typer(
    add_completion=False,
    help="An executable registry of graph algorithm semantics.",
    no_args_is_help=True,
)
console = Console()


def parse_overrides(values: list[str] | None) -> dict[str, Any]:
    """Turn `--set name=value` pairs into canonical parameters.

    Values go through the YAML parser, so `damping=0.9` is a float and
    `weight_property=false` is the boolean that means explicitly unweighted.
    """
    overrides: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            raise typer.BadParameter(f"expected name=value, got {item!r}")
        name, _, raw = item.partition("=")
        overrides[name.strip()] = yaml.safe_load(raw)
    return overrides
