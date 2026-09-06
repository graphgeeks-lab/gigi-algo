"""The agent surface: the same three functions, addressed by something that is
not a person.

`cli/` renders the registry for a terminal and `site/` for a browser. This
renders it for a model: a list of tools with JSON schemas, served over MCP or
emitted as a manifest for any other runtime.

Reporting, not capability. Every handler in `tools.py` is a call into
`registry`, `ask` or `harness`; nothing here computes an answer of its own, and
if something starts to, it belongs in the library instead.
"""

from __future__ import annotations

from gigi.agent.manifest import manifest
from gigi.agent.tools import TOOLS, call

__all__ = ["TOOLS", "call", "manifest"]
