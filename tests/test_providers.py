"""A model may find. It may not speak.

`gigi ask` will use a model to choose *which registry entries* a question is
about, because word overlap cannot read paraphrase. It is never asked what a
method does, and nothing it writes is shown to anyone.

That is only a safe trade if the validation actually holds, so most of this
file is a model behaving badly: inventing ids, returning prose, returning
nothing, timing out. The requirement in every case is the same -- the user gets
a true answer from the registry, or an honest "nothing matches". Never a
fabricated method.

`tests/test_ask.py` covers the word-matching path; these are the additions a
model brings.
"""

from __future__ import annotations

import pytest

from gigi import registry
from gigi.ask import MODEL_SCORE, ask, catalogue, parse_ids, resolve, search_with_model
from gigi.providers import PROVIDERS, first_available
from gigi.providers._http import ProviderError


class FakeProvider:
    """A model that returns whatever it was constructed with."""

    NAME = "fake"

    def __init__(self, reply="", raises=None):
        self.reply = reply
        self.raises = raises
        self.prompts = []

    def complete(self, system, question, max_tokens=512):
        self.prompts.append((system, question))
        if self.raises:
            raise self.raises
        return self.reply


def _json(*ids):
    inner = ", ".join(f'"{i}"' for i in ids)
    return f'{{"ids": [{inner}]}}'


# --- the reason this exists ---------------------------------------------------


def test_a_model_reads_paraphrase_that_word_matching_misses():
    """The case that prompted all of this. "matter most" shares no word with
    "important", so word matching finds degree centrality and silently drops
    PageRank -- which is exactly the method the user was asking for."""
    question = "which nodes matter most"

    by_words = ask(question)
    by_model = ask(question, provider=FakeProvider(
        _json("simple_node_importance", "recursive_node_influence")
    ))

    assert by_words.answered_by == ["degree_centrality"]
    assert by_model.answered_by == ["degree_centrality", "pagerank"]


def test_the_model_is_only_ever_shown_the_catalogue_and_the_question():
    """It is not asked to explain anything, and it is not given prose to
    embellish. The prompt is a closed list of ids and the user's words."""
    provider = FakeProvider(_json("pagerank"))
    ask("who are the influencers", provider=provider)

    system, question = provider.prompts[0]
    assert question == "who are the influencers"
    assert "JSON only" in system
    assert "pagerank" in system, "the catalogue should be in the system prompt"


def test_the_catalogue_only_contains_things_that_exist():
    """A model choosing from this list can only choose real entries. That is
    the first of two defences; `resolve` is the one that does not trust it."""
    known = set(registry.list_methods()) | {p.id for p in registry.list_problems()}
    known |= {f.id for f in registry.list_families()}

    for line in catalogue().splitlines():
        # `- <id> (<kind>): ...` -- the id is the first token, which is the
        # whole point of the format. An earlier one put the kind first and
        # models returned "problem" as an id.
        entry_id = line.split(" ", 1)[1].split(" ", 1)[0]
        assert entry_id in known, f"catalogue names {entry_id!r}, which does not exist"


# --- a model behaving badly ---------------------------------------------------


def test_an_invented_method_never_reaches_the_user():
    """The whole safety property. A model that answers with plausible nonsense
    must not be able to put that nonsense in front of somebody."""
    provider = FakeProvider(_json("quantum_pagerank", "blockchain_centrality"))
    answer = ask("which nodes matter most", provider=provider)

    assert answer.matched_by == "keywords", "should have fallen back"
    for method_id in answer.answered_by:
        assert registry.method_exists(method_id)
    assert "quantum_pagerank" not in str(answer)


def test_a_near_miss_id_is_dropped_not_guessed():
    """`pagernak` is not `pagerank`. Fuzzy-matching a model's typo would be
    inventing a match on its behalf."""
    assert resolve(["pagernak", "PageRank", "pagerank "]) == []
    assert [m.id for m in resolve(["pagerank"])] == ["pagerank"]


def test_a_partly_invented_answer_keeps_only_the_real_part():
    matches = resolve(["pagerank", "made_up_thing", "degree_centrality"])
    assert [m.id for m in matches] == ["pagerank", "degree_centrality"]


@pytest.mark.parametrize(
    "reply",
    [
        "",
        "I think you want PageRank!",
        "{",
        '{"ids": "pagerank"}',
        '{"ids": [{"id": "pagerank"}]}',
        '{"methods": ["pagerank"]}',
        "null",
    ],
)
def test_a_reply_that_is_not_the_agreed_shape_yields_nothing(reply):
    assert parse_ids(reply) == []


@pytest.mark.parametrize(
    "reply,expected",
    [
        ('{"ids": ["pagerank"]}', ["pagerank"]),
        ('```json\n{"ids": ["pagerank"]}\n```', ["pagerank"]),
        ('Sure. {"ids": ["pagerank", "bfs"]} Hope that helps!', ["pagerank", "bfs"]),
    ],
)
def test_json_is_found_even_when_wrapped(reply, expected):
    """Models fence and preamble however they feel that day. Losing a match to
    a stray backtick is a bad reason to fall back."""
    assert parse_ids(reply) == expected


def test_a_dead_endpoint_falls_back_rather_than_failing():
    """`gigi ask` working offline is not negotiable."""
    answer = ask("which nodes matter most",
                 provider=FakeProvider(raises=ProviderError("connection refused")))

    assert answer.matched_by == "keywords"
    assert answer.answered_by == ["degree_centrality"]


def test_any_exception_at_all_falls_back():
    """Not just ProviderError. A provider bug must not take out the command."""
    answer = ask("which nodes matter most", provider=FakeProvider(raises=RuntimeError("boom")))
    assert answer.matched_by == "keywords"


def test_a_model_that_matches_nothing_falls_back_to_words():
    """An empty list is a legitimate model answer, but the word matcher may
    still know something -- so it gets a turn before we give up."""
    answer = ask("which nodes matter most", provider=FakeProvider(_json()))
    assert answer.matched_by == "keywords"
    assert answer.answered_by


def test_a_model_cannot_manufacture_an_answer_to_an_unanswerable_question():
    """Even told to, it cannot make Gigi claim to do community detection: the
    ids resolve, but `answered_by` comes from the registry, not the model."""
    answer = ask("how do I find communities",
                 provider=FakeProvider(_json("community_grouping")))

    assert answer.matched_by == "fake"
    assert answer.unanswered
    assert answer.answered_by == []


# --- provenance is visible ----------------------------------------------------


def test_the_answer_records_which_path_matched_it():
    assert ask("which nodes matter most").matched_by == "keywords"
    assert ask("x", provider=FakeProvider(_json("pagerank"))).matched_by == "fake"


def test_model_matches_clear_the_relevance_floor():
    """A model has already made the judgement the floor exists to make, so its
    matches must not then be filtered out by it."""
    answer = ask("anything", provider=FakeProvider(_json("pagerank")))
    assert answer.confident
    assert answer.matches[0].score == MODEL_SCORE


def test_model_ordering_survives_into_the_ranking():
    matches = resolve(["degree_centrality", "pagerank"])
    assert matches[0].id == "degree_centrality"
    assert matches[0].score > matches[1].score


# --- the provider registry ----------------------------------------------------


def test_no_provider_is_configured_by_accident(monkeypatch):
    """Nothing should talk to a model because an unrelated variable happened to
    be set. Absent keys means absent providers."""
    for variable in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GIGI_OLLAMA", "OLLAMA_HOST"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(PROVIDERS["ollama"], "available", lambda: False)

    assert first_available() is None


def test_a_key_makes_its_provider_available(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert PROVIDERS["anthropic"].available()


def test_a_provider_without_a_key_refuses_rather_than_calling_out(monkeypatch):
    """It must fail before opening a socket, not after."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        PROVIDERS["anthropic"].complete("system", "question")


@pytest.mark.parametrize("name", sorted(PROVIDERS))
def test_every_provider_has_the_same_shape(name):
    """`ask.py` calls these interchangeably; a missing attribute would only
    show up on the machine that had that provider configured."""
    module = PROVIDERS[name]
    assert isinstance(module.NAME, str)
    assert callable(module.available)
    assert callable(module.complete)
    assert isinstance(module.model(), str)


def test_the_model_is_overridable_without_editing_code(monkeypatch):
    monkeypatch.setenv("GIGI_ANTHROPIC_MODEL", "claude-something-newer")
    assert PROVIDERS["anthropic"].model() == "claude-something-newer"


def test_openai_can_point_at_a_local_server(monkeypatch):
    """The reason this provider shape is worth having: vLLM, llama.cpp and
    LM Studio all speak it."""
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8000/v1/")
    assert PROVIDERS["openai"].base_url() == "http://localhost:8000/v1"


def test_search_with_model_returns_a_list_not_an_exception():
    """The contract `ask` relies on for its fallback."""
    assert search_with_model("q", FakeProvider(raises=RuntimeError())) == []
    assert search_with_model("q", FakeProvider("nonsense")) == []


# --- the HTTP path, against a real socket -------------------------------------
#
# The fakes above replace `complete()` entirely, so they never exercise urllib,
# the headers, the URL, or the JSON round trip. This does, against a local
# server. What it cannot check is whether the vendors' APIs really have these
# shapes -- that is written from their documentation and is the one part of this
# file taken on trust.


@pytest.fixture()
def fake_api():
    """A local HTTP server that records the request and returns a canned reply."""
    import json as _json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            received["path"] = self.path
            received["headers"] = dict(self.headers)
            received["body"] = _json.loads(self.rfile.read(length))

            payload = _json.dumps(
                {"choices": [{"message": {"content": '{"ids": ["pagerank"]}'}}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1", received
    server.shutdown()


def test_the_openai_request_is_well_formed(monkeypatch, fake_api):
    """Everything except the vendor's contract: URL, headers, body shape, and
    parsing a genuine HTTP response."""
    url, received = fake_api
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", url)
    monkeypatch.setenv("GIGI_OPENAI_MODEL", "test-model")

    reply = PROVIDERS["openai"].complete("be terse", "which nodes matter most")

    assert reply == '{"ids": ["pagerank"]}'
    assert received["path"] == "/v1/chat/completions"
    assert received["headers"]["Authorization"] == "Bearer sk-test"
    assert received["body"]["model"] == "test-model"
    assert [m["role"] for m in received["body"]["messages"]] == ["system", "user"]


def test_a_real_round_trip_reaches_an_answer(monkeypatch, fake_api):
    """End to end over a socket: question in, validated registry ids out."""
    url, _ = fake_api
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", url)

    answer = ask("which nodes matter most", provider=PROVIDERS["openai"])

    assert answer.matched_by == "openai"
    assert answer.answered_by == ["pagerank"]


def test_an_http_error_becomes_a_provider_error(monkeypatch):
    """A 401 from a bad key must not escape as an urllib traceback."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-wrong")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1/v1")

    with pytest.raises(ProviderError, match="could not reach|HTTP"):
        PROVIDERS["openai"].complete("system", "question")


# --- the substitution rule ----------------------------------------------------
#
# Found against the live OpenAI API, not by reasoning about it. Asked "how do I
# find communities", gpt-4o-mini returns the right question *and* the method
# people mistake for it *and* a second reading that method does answer:
#
#   ["community_grouping", "community", "connected_components",
#    "component_membership"]
#
# Every id is real, so validation passes. Connected components then answered
# via `component_membership` -- exactly the substitution the registry documents
# as a mistake, arrived at through the back door.


def test_a_method_cannot_substitute_for_a_question_it_disclaims():
    """The live failure, pinned. `community_grouping` is answered by nothing;
    `connected_components` declares it out of scope and must not be offered
    instead, even though it does answer the second-ranked reading."""
    provider = FakeProvider(_json(
        "community_grouping", "community", "connected_components", "component_membership"
    ))
    answer = ask("how do I find communities in my graph", provider=provider)

    assert answer.matched_by == "fake"
    assert answer.unanswered, "nothing here does community detection"
    assert answer.answered_by == []
    assert ("community_grouping", "connected_components") in answer.not_answered_by


def test_a_disclaimer_does_not_silence_a_method_that_answers_another_reading():
    """The counterpart, and why the rule is narrow. "Which nodes are most
    important" is genuinely ambiguous: degree centrality answers one reading,
    PageRank the other, and PageRank disclaiming the first must not remove it
    from the second."""
    provider = FakeProvider(_json(
        "simple_node_importance", "recursive_node_influence", "degree_centrality", "pagerank"
    ))
    answer = ask("which nodes are most important", provider=provider)

    assert set(answer.answered_by) == {"degree_centrality", "pagerank"}


def test_the_rule_needs_the_top_question_to_be_unanswerable():
    """If the best reading has a method, a disclaimer means only "not this
    particular problem" -- not "not this question"."""
    from gigi import registry

    assert not registry.methods_for_problem("community_grouping")
    assert registry.methods_for_problem("simple_node_importance")
