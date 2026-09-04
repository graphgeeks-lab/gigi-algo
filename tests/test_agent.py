"""The agent surface: tools, manifests, and the MCP server.

Three things need to stay true here, and none of them are about the protocol.

1. **Every tool is callable as advertised.** A schema that names `method` while
   the handler takes `method_id` fails every call, and an agent has no way to
   discover why. That bug existed for ten minutes and this is the test that
   would have caught it.
2. **Errors come back as data.** An agent that receives a traceback learns
   nothing it can act on.
3. **The gate holds.** A `frontier` method is not runnable just because the
   caller is a model rather than a person.
"""

from __future__ import annotations

import io
import json

import pytest

from gigi.agent import TOOLS, call, manifest
from gigi.agent.manifest import FORMATS
from gigi.agent.mcp import PROTOCOL_VERSION, handle, serve

# Valid arguments for every tool. Keyed by name so a new tool without a case
# here fails `test_every_tool_is_callable_as_advertised` rather than going
# untested.
CALLS = {
    "gigi_ask": {"question": "which nodes matter most"},
    "gigi_list_methods": {},
    "gigi_describe_method": {"method": "pagerank"},
    "gigi_why": {"method": "pagerank", "dataset": "road-distances-small"},
    "gigi_list_datasets": {"kind": "graph"},
    "gigi_run": {
        "method": "connected_components",
        "backend": "reference",
        "dataset": "disconnected-small",
    },
    "gigi_compare": {"method": "connected_components", "dataset": "disconnected-small"},
    "gigi_verify": {"method": "cosine_similarity"},
}


# --- the tools ----------------------------------------------------------------


def test_every_tool_has_a_case_here():
    """A tool nobody exercised is a tool nobody knows works."""
    assert set(CALLS) == {tool.name for tool in TOOLS}


@pytest.mark.parametrize("name", sorted(CALLS))
def test_every_tool_is_callable_as_advertised(name):
    """The handler's parameters must match the schema it publishes. This is the
    check that catches a rename on one side only."""
    result = call(name, CALLS[name])
    assert isinstance(result, dict)
    assert "error" not in result, result.get("error")


@pytest.mark.parametrize("name", sorted(CALLS))
def test_every_tool_returns_json(name):
    """An agent receives JSON. A result holding a pydantic model or an enum
    would serialise somewhere far from here, or not at all."""
    json.dumps(call(name, CALLS[name]))


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.name)
def test_every_tool_describes_itself(tool):
    assert len(tool.description) > 40, "an agent picks tools by description alone"
    assert tool.schema["type"] == "object"
    for required in tool.schema["required"]:
        assert required in tool.schema["properties"]


# --- errors are data ----------------------------------------------------------


def test_an_unknown_tool_lists_the_known_ones():
    result = call("gigi_nope")
    assert "unknown tool" in result["error"]
    assert set(result["known"]) == {t.name for t in TOOLS}


def test_a_bad_argument_says_so_rather_than_raising():
    result = call("gigi_describe_method", {"wrong": "pagerank"})
    assert "error" in result


def test_an_unknown_method_is_an_error_not_a_crash():
    result = call("gigi_describe_method", {"method": "pagernak"})
    assert "error" in result
    assert "pagernak" in result["error"]


def test_a_failed_run_is_reported_not_raised():
    """A backend that cannot take this input is a status, exactly as it is
    everywhere else in Gigi."""
    result = call(
        "gigi_run",
        {"method": "pagerank", "backend": "networkx", "dataset": "vectors-small"},
    )
    assert result["status"] == "error"
    assert "takes a graph" in result["status_detail"]
    # And crucially: the *tool* did not fail, so nothing flags this as an
    # error to the model. It is a result, and a true one.
    assert "error" not in result


# --- the ask tool carries its own guardrail -----------------------------------


def test_the_ask_tool_tells_an_agent_not_to_improvise():
    """The tool result is the only thing a model sees. If it goes back empty
    with no instruction, the model fills the silence."""
    result = call("gigi_ask", {"question": "how do I train a neural network"})

    assert result["recognised"] is False
    assert not result["answered_by"]
    assert "do not" in result["guidance"].lower()


def test_the_ask_tool_flags_a_question_nothing_answers():
    result = call("gigi_ask", {"question": "how do I find communities"})
    assert result["nothing_answers_it"] is True
    assert result["answered_by"] == []


# --- manifests ----------------------------------------------------------------


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_renders_every_tool(fmt):
    rendered = manifest(fmt)
    assert len(rendered) == len(TOOLS)
    json.dumps(rendered)


def test_each_format_puts_the_schema_where_its_runtime_expects_it():
    assert "inputSchema" in manifest("mcp")[0]
    assert "input_schema" in manifest("anthropic")[0]
    assert manifest("openai")[0]["type"] == "function"
    assert "parameters" in manifest("openai")[0]["function"]


def test_an_unknown_format_names_the_known_ones():
    with pytest.raises(ValueError, match="anthropic"):
        manifest("cuneiform")


# --- MCP ----------------------------------------------------------------------


def test_initialize_reports_the_protocol_and_the_version():
    from gigi import __version__

    result = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})["result"]
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["capabilities"]["tools"] == {}
    assert result["serverInfo"] == {"name": "gigi", "version": __version__}


def test_a_notification_gets_no_reply():
    """A message with no id must produce no response. Reply to one and a
    conforming client waits forever for a request it never made."""
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_list_matches_the_registry():
    listed = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert [t["name"] for t in listed] == [t.name for t in TOOLS]


def test_a_tool_call_comes_back_as_text_content():
    response = handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "gigi_list_methods", "arguments": {}},
    })
    body = json.loads(response["result"]["content"][0]["text"])

    assert not response["result"]["isError"]
    assert {m["id"] for m in body["methods"]} >= {"pagerank", "cosine_similarity"}


def test_a_tool_error_is_flagged_but_still_returned():
    """`isError` marks it; the message still reaches the model, which is what
    lets it correct the call rather than give up."""
    response = handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "gigi_nope", "arguments": {}},
    })
    assert response["result"]["isError"] is True
    assert "unknown tool" in response["result"]["content"][0]["text"]


def test_an_unknown_protocol_method_is_a_jsonrpc_error():
    """Different from a tool error: the client got the protocol wrong, not the
    arguments."""
    response = handle({"jsonrpc": "2.0", "id": 5, "method": "tools/nope"})
    assert response["error"]["code"] == -32601


def test_the_loop_survives_malformed_input():
    """One bad line must not end the session."""
    stdin = io.StringIO(
        "not json\n"
        '{"jsonrpc":"2.0","id":1,"method":"ping"}\n'
        "\n"
        '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
    )
    stdout = io.StringIO()
    serve(stdin, stdout)

    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert "invalid JSON" in responses[0]["error"]["message"]
    assert responses[1]["result"] == {}
    assert len(responses[2]["result"]["tools"]) == len(TOOLS)


def test_every_response_is_one_line_of_json():
    """The transport is line-delimited. A pretty-printed response, or anything
    else written to stdout, corrupts the stream for the client."""
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
    stdout = io.StringIO()
    serve(stdin, stdout)

    assert len(stdout.getvalue().strip().splitlines()) == 1


# --- the gate holds for a caller that is not a person -------------------------


@pytest.fixture()
def frontier_registry(tmp_path, monkeypatch):
    """A registry holding one `frontier` method, built the way
    tests/test_maturity.py builds it."""
    import shutil

    from gigi import maturity, registry
    from gigi.paths import methods_dir

    root = tmp_path / "methods"
    destination = root / "frontier_check"
    shutil.copytree(methods_dir() / "degree_centrality", destination)

    spec_path = destination / "method.yaml"
    text = spec_path.read_text(encoding="utf-8")
    text = text.replace("id: degree_centrality", "id: frontier_check", 1)
    text = text.replace("maturity: emerging", "maturity: frontier", 1)
    spec_path.write_text(text, encoding="utf-8")

    monkeypatch.setenv("GIGI_METHODS_DIR", str(root))
    monkeypatch.delenv(maturity.FRONTIER_ENV, raising=False)
    registry.load_method.cache_clear()
    yield "frontier_check"
    registry.load_method.cache_clear()


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("gigi_run", {"backend": "reference", "dataset": "tiny-directed"}),
        ("gigi_compare", {"dataset": "tiny-directed"}),
        ("gigi_verify", {}),
    ],
)
def test_an_agent_cannot_run_a_frontier_method(frontier_registry, tool, arguments):
    """The gate lives in the harness so every caller inherits it. An agent is
    not an exception, and this is the place it would be tempting to make one.

    The refusal arrives as a readable error rather than a traceback -- the
    model should be able to tell the user *why* it declined.
    """
    result = call(tool, {"method": frontier_registry, **arguments})

    assert "error" in result
    assert "frontier" in result["error"].lower()


def test_the_gate_does_not_block_everything_else(frontier_registry):
    """A guard that refused every method would pass the test above and be
    useless."""
    result = call("gigi_describe_method", {"method": frontier_registry})
    assert result["maturity"] == "frontier"
    assert "error" not in result
