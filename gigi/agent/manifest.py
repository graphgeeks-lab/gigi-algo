"""The tool list, in whatever shape a runtime expects.

Three renderings of one definition. They differ only in where the schema hangs
and what the key is called, which is exactly the kind of difference that should
live in one small function rather than in three copies of the tool list.
"""

from __future__ import annotations

from typing import Any

from gigi.agent.tools import TOOLS

FORMATS = ("mcp", "anthropic", "openai")


def manifest(fmt: str = "mcp") -> list[dict[str, Any]]:
    """Every tool, rendered for one runtime."""
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r} (known: {', '.join(FORMATS)})")

    if fmt == "anthropic":
        return [
            {"name": t.name, "description": t.description, "input_schema": t.schema}
            for t in TOOLS
        ]
    if fmt == "openai":
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.schema,
                },
            }
            for t in TOOLS
        ]
    return [
        {"name": t.name, "description": t.description, "inputSchema": t.schema}
        for t in TOOLS
    ]
