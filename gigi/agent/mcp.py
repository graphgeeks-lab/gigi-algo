"""An MCP server over stdio, in about a hundred lines.

Hand-rolled rather than taking the `mcp` package as a dependency. The protocol
surface Gigi needs is four methods and a JSON-RPC envelope, and a dependency
that exists to save fifty lines is a dependency a contributor has to install,
a version to pin, and a thing that can break the wheel. If Gigi ever needs
resources, prompts, sampling or progress, that trade changes and the package is
the right answer.

Speaks JSON-RPC 2.0, one message per line, on stdin and stdout. **Nothing may
ever be printed to stdout except a response** -- a stray print corrupts the
stream and the client sees a parse error rather than whatever was printed. Logs
go to stderr.

    $ gigi mcp

    # Claude Code / Claude Desktop config:
    {"mcpServers": {"gigi": {"command": "gigi", "args": ["mcp"]}}}
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from gigi.agent.manifest import manifest
from gigi.agent.tools import call

PROTOCOL_VERSION = "2024-11-05"

# JSON-RPC error codes, from the spec. Named because a bare -32601 in a return
# statement tells a reader nothing.
METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603


def _server_info() -> dict[str, Any]:
    from gigi import __version__

    return {"name": "gigi", "version": __version__}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    """One request in, one response out. None means "send nothing".

    Notifications -- messages with no `id` -- get no reply, which the spec
    requires and which a client will hang on if got wrong.
    """
    method = message.get("method")
    message_id = message.get("id")

    if message_id is None:
        return None

    if method == "initialize":
        return _ok(message_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": _server_info(),
        })

    if method == "ping":
        return _ok(message_id, {})

    if method == "tools/list":
        return _ok(message_id, {"tools": manifest("mcp")})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name", "")
        result = call(name, params.get("arguments") or {})
        # An unknown tool or a bad argument is a *result* an agent can act on,
        # not a protocol error. Only `isError` marks it, so the model still
        # sees the message and can correct the call.
        return _ok(message_id, {
            "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            "isError": bool(isinstance(result, dict) and result.get("error")),
        })

    return _error(message_id, METHOD_NOT_FOUND, f"unknown method {method!r}")


def _ok(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, text: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": text}}


def serve(stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    """Read requests until stdin closes.

    The streams are arguments so the loop can be tested without a subprocess,
    which is the difference between this being covered and being hoped about.
    """
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            _write(stdout, _error(None, INTERNAL_ERROR, f"invalid JSON: {exc}"))
            continue

        try:
            response = handle(message)
        except Exception as exc:  # a tool bug must not take the server down
            response = _error(message.get("id"), INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")

        if response is not None:
            _write(stdout, response)


def _write(stdout: TextIO, payload: dict[str, Any]) -> None:
    stdout.write(json.dumps(payload, default=str) + "\n")
    stdout.flush()
