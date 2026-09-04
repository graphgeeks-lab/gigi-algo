"""The tools an agent may call, defined once.

One list, rendered three ways: as an MCP `tools/list` reply, as an Anthropic
tool block, as an OpenAI function. Adding a tool is adding an entry here, the
same shape as adding a backend -- a dict, not a plugin system.

Every handler is a thin call into `registry`, `ask` or `harness`. Nothing here
computes: if a tool ever needs logic of its own, that logic belongs in the
library and the tool belongs to the reporting layer, exactly as `cli/` does.

Execution tools honour the maturity gate. `frontier` methods raise
`FrontierBlocked` inside the harness, and every caller inherits that -- an agent
is not a special case, and this is the one place it would be tempting to make it
one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gigi import ask as ask_module
from gigi import registry
from gigi.data import describe, list_datasets, load_dataset, profile_dataset


@dataclass(frozen=True)
class Tool:
    """One callable operation, and the schema an agent needs to call it."""

    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[..., Any]


def _string(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


# --- handlers ------------------------------------------------------------------


def _ask(question: str) -> dict[str, Any]:
    answer = ask_module.ask(question)
    return {
        "question": answer.question,
        "recognised": not answer.found_nothing,
        "answered_by": answer.answered_by,
        "nothing_answers_it": answer.unanswered,
        "problems": answer.problems,
        "not_for": [
            {"problem": problem, "method": method, "reason": "the method declares this out of scope"}
            for problem, method in answer.not_answered_by
        ],
        "matches": [
            {"kind": m.kind, "id": m.id, "title": m.title, "score": round(m.score, 3)}
            for m in answer.matches
        ],
        "guidance": _ask_guidance(answer),
    }


def _ask_guidance(answer: ask_module.Answer) -> str:
    """The sentence that stops an agent inventing an answer.

    Said plainly, because the failure being prevented is an agent reading an
    empty result as permission to improvise.
    """
    if answer.found_nothing:
        return (
            "Nothing in the registry matches this question. Say so. Do not "
            "recommend a method from general knowledge -- this registry's value "
            "is that everything in it is verified, and a suggestion from outside "
            "it carries none of that."
        )
    if answer.unanswered:
        return (
            "The registry recognises this question but no method here answers "
            "it. Say that explicitly, and name the methods that declare it out "
            "of scope rather than offering the nearest one."
        )
    return (
        "Recommend only the methods in `answered_by`. Check `not_for` before "
        "suggesting anything else, and cite method ids so the claim can be "
        "checked with `gigi show <id>`."
    )


def _list_methods(domain: str | None = None) -> dict[str, Any]:
    method_ids = registry.methods_in_domain(domain) if domain else registry.list_methods()
    return {
        "methods": [
            {
                "id": method_id,
                "name": spec.name,
                "kind": spec.kind.value,
                "domain": registry.domain_of(spec),
                "family": spec.family,
                "maturity": spec.maturity.value,
                "summary": spec.summary.strip(),
                "problems": spec.problems,
                "backends": registry.implemented_backends(method_id),
            }
            for method_id in method_ids
            for spec in [registry.load_method(method_id)]
        ]
    }


def _describe_method(method: str) -> dict[str, Any]:
    spec = registry.load_method(method)
    return {
        "id": spec.id,
        "name": spec.name,
        "kind": spec.kind.value,
        "domain": registry.domain_of(spec),
        "maturity": spec.maturity.value,
        "summary": spec.summary.strip(),
        "answers": [registry.load_problem(p).question.strip() for p in spec.problems],
        "does_not_answer": [
            registry.load_problem(p).question.strip() for p in spec.intent.not_for
        ],
        "ai_context": spec.ai_context.model_dump() if spec.ai_context else None,
        "maths": spec.maths.model_dump(mode="json"),
        "parameters": [p.model_dump(mode="json") for p in spec.parameters],
        "output": spec.output.model_dump(mode="json"),
        "backends": {name: s.model_dump() for name, s in spec.backends.items()},
        "divergences": [d.model_dump(mode="json") for d in spec.divergences],
        "datasets": spec.datasets,
    }


def _why(method: str, dataset: str | None = None) -> dict[str, Any]:
    from gigi import semantics
    from gigi.graph import GraphData

    spec = registry.load_method(method)
    result: dict[str, Any] = {
        "method": spec.id,
        "answers": [registry.load_problem(p).question.strip() for p in spec.problems],
        "does_not_answer": [
            {
                "question": registry.load_problem(p).question.strip(),
                "use_instead": registry.methods_for_problem(p) or None,
            }
            for p in spec.intent.not_for
        ],
        "reads_your_data_as": [i.model_dump(mode="json") for i in spec.semantic_interpretations],
    }
    if dataset is None:
        return result

    data = load_dataset(dataset)
    result["dataset"] = dataset
    if isinstance(data, GraphData):
        findings = semantics.check_graph(spec, data)
        result["findings"] = [
            {"column": f.column, "serious": f.serious, "question": f.question()} for f in findings
        ]
    else:
        result["findings"] = []
        result["note"] = "no column-meaning check for this kind of data yet"
    return result


def _list_datasets(kind: str | None = None) -> dict[str, Any]:
    return {
        "datasets": [
            {
                "id": dataset_id,
                "kind": profile.kind,
                "shape": describe(profile),
                "description": data.metadata.description.strip(),
            }
            for dataset_id in list_datasets(kind)
            for data in [load_dataset(dataset_id)]
            for profile in [profile_dataset(data)]
        ]
    }


def _run(method: str, backend: str, dataset: str, parameters: dict | None = None) -> dict[str, Any]:
    from gigi.harness import run

    result = run(method, backend, dataset, parameters=parameters or {})
    return {
        "method": result.method_id,
        "backend": result.backend,
        "backend_version": result.backend_version,
        "dataset": result.dataset_id,
        "status": result.status.value,
        # Named apart from the envelope's `error`, which means *the tool call
        # failed*. A run that reports a backend failure is a successful tool
        # call returning a real result, and MCP must not flag it as an error.
        "status_detail": result.error,
        "requested_parameters": result.requested_parameters,
        "effective_parameters": result.effective_parameters,
        "result": result.result.model_dump(mode="json") if result.result else None,
        "invariants": [i.model_dump() for i in result.invariants],
        "duration_ms": round(result.total_duration_ms, 2),
    }


def _compare(method: str, dataset: str, parameters: dict | None = None) -> dict[str, Any]:
    from gigi.harness import compare

    runs, comparisons = compare(method, dataset, parameters=parameters or {})
    return {
        "method": method,
        "dataset": dataset,
        "runs": [
            {
                "backend": r.backend,
                "version": r.backend_version,
                "status": r.status.value,
                "status_detail": r.error,
            }
            for r in runs
        ],
        "comparisons": [
            {
                "backend": c.backend_b,
                "agrees_with_reference": c.equivalent,
                "metrics": c.metrics,
                "notes": c.notes,
            }
            for c in comparisons
        ],
    }


def _verify(method: str) -> dict[str, Any]:
    from gigi.harness import verify

    report = verify(method)
    return {
        "method": report.method_id,
        "status": report.status,
        "conclusion": report.conclusion,
        "backends": report.backends,
        "backend_versions": report.backend_versions,
        "undeclared_differences": [d.model_dump(mode="json") for d in report.undeclared_differences],
        "divergence_checks": [c.model_dump(mode="json") for c in report.divergence_checks],
    }


# --- the registry --------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        "gigi_ask",
        "Ask the registry a question in plain language. Returns the methods that "
        "answer it, the ones that explicitly do not, and -- importantly -- says "
        "when nothing in the registry answers it at all. Start here.",
        _object({"question": _string("A question about graphs, methods or data.")}, ["question"]),
        _ask,
    ),
    Tool(
        "gigi_list_methods",
        "Every method in the registry, with its domain, family, maturity and the "
        "problems it claims to solve.",
        _object({"domain": _string("Optional domain id, e.g. 'graph' or 'similarity'.")}),
        _list_methods,
    ),
    Tool(
        "gigi_describe_method",
        "Everything the registry claims about one method: the mathematics, its "
        "invariants, where its definition is under-determined, its parameters, "
        "and every recorded divergence between backends.",
        _object({"method": _string("Method id, e.g. 'pagerank'.")}, ["method"]),
        _describe_method,
    ),
    Tool(
        "gigi_why",
        "What a method answers, what it does not, and how it will read the "
        "user's data. With a dataset, checks the method's assumptions against "
        "the actual columns -- this is what catches a distance column being read "
        "as a strength.",
        _object(
            {
                "method": _string("Method id."),
                "dataset": _string("Optional dataset id to check assumptions against."),
            },
            ["method"],
        ),
        _why,
    ),
    Tool(
        "gigi_list_datasets",
        "The fixtures available to run against, with their kind and shape.",
        _object({"kind": _string("Optional: 'graph' or 'vectors'.")}),
        _list_datasets,
    ),
    Tool(
        "gigi_run",
        "Execute one method on one backend against one dataset. Returns the "
        "result, the parameters the backend actually used, and which invariants "
        "held.",
        _object(
            {
                "method": _string("Method id."),
                "backend": _string("Backend name, e.g. 'reference', 'networkx', 'scipy'."),
                "dataset": _string("Dataset id."),
                "parameters": {"type": "object", "description": "Optional parameter overrides."},
            },
            ["method", "backend", "dataset"],
        ),
        _run,
    ),
    Tool(
        "gigi_compare",
        "Run every available backend on one dataset and report where they "
        "disagree with the reference implementation.",
        _object(
            {
                "method": _string("Method id."),
                "dataset": _string("Dataset id."),
                "parameters": {"type": "object", "description": "Optional parameter overrides."},
            },
            ["method", "dataset"],
        ),
        _compare,
    ),
    Tool(
        "gigi_verify",
        "Check the registry's claims about a method against reality: do the "
        "backends agree where it says they agree, and do its declared "
        "divergences still reproduce?",
        _object({"method": _string("Method id.")}, ["method"]),
        _verify,
    ),
]

BY_NAME = {tool.name: tool for tool in TOOLS}


def call(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Invoke one tool by name. Errors come back as data, not exceptions.

    An agent that gets a traceback learns nothing it can act on; one that gets
    `{"error": "unknown method 'pagernak'"}` can fix the call. The exception is
    never swallowed silently -- the message is the whole point of returning it.
    """
    tool = BY_NAME.get(name)
    if tool is None:
        return {"error": f"unknown tool {name!r}", "known": sorted(BY_NAME)}
    try:
        return tool.handler(**(arguments or {}))
    except TypeError as exc:  # wrong or missing arguments
        return {"error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
