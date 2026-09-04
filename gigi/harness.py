"""Run, compare, verify.

Three functions. The CLI, the Python API and any future agent tool call these
same three -- there is no second code path.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from gigi import registry
from gigi.adapters import available_engines, engine_versions, get_engine
from gigi.graph import GraphData, load_graph, profile_graph
from gigi.models import (
    AlgorithmSpec,
    Comparison,
    Difference,
    DivergenceCheck,
    RunResult,
    RunStatus,
    VerificationReport,
)
from gigi.invariants import check_all
from gigi.maturity import check_runnable
from gigi.results import compare_results, normalize_node_score

REFERENCE = "reference"

# `weight_property` is tri-state and that is the point:
#   None   -> let the engine apply its own default (which is what diverges)
#   False  -> explicitly unweighted
#   "name" -> use this edge attribute
WEIGHT_PROPERTY = "weight_property"


def default_parameters(spec: AlgorithmSpec) -> dict[str, Any]:
    """What a caller gets when they ask for nothing: Gigi's canonical defaults
    where the community agrees on one, and the engine's own default everywhere
    else. This is the configuration under which engines disagree."""
    return {p.name: p.common_default for p in spec.parameters}


def explicit_parameters(spec: AlgorithmSpec, graph: GraphData) -> dict[str, Any]:
    """Every ambiguous parameter pinned, so that any remaining disagreement is
    a real semantic difference rather than a difference of defaults.

    Tolerances and caps come from `verification.parameters` in the spec;
    `weight_property` is derived from the dataset because only the dataset
    knows whether there is a weight column to use.
    """
    params = default_parameters(spec)
    params.update(spec.verification.parameters)
    if WEIGHT_PROPERTY in params:
        params[WEIGHT_PROPERTY] = graph.weight_column or False
    return params


def resolve_parameters(
    spec: AlgorithmSpec,
    graph: GraphData,
    overrides: dict[str, Any] | None = None,
    explicit: bool = False,
) -> dict[str, Any]:
    """Canonical parameters for one run: defaults, then pinned values if
    `explicit`, then whatever the caller asked for."""
    params = explicit_parameters(spec, graph) if explicit else default_parameters(spec)
    params.update(overrides or {})
    return params


def _load(algorithm: str | AlgorithmSpec) -> AlgorithmSpec:
    return algorithm if isinstance(algorithm, AlgorithmSpec) else registry.load_algorithm(algorithm)


def _load_graph(graph: str | GraphData) -> GraphData:
    return graph if isinstance(graph, GraphData) else load_graph(graph)


def run(
    algorithm: str | AlgorithmSpec,
    engine: str,
    graph: str | GraphData,
    parameters: dict[str, Any] | None = None,
    allow_frontier: bool = False,
) -> RunResult:
    """Execute one algorithm on one engine and return a fully described run.

    An *engine* failure is a RunResult with a status, never an exception:
    verification needs to report what did not run as much as what did. A
    *policy* refusal is different -- a frontier algorithm without opt-in raises
    `FrontierBlocked`, because there is no result to describe and the caller
    asked for something they are not allowed to have.
    """
    spec = _load(algorithm)
    check_runnable(spec, allow_frontier)
    data = _load_graph(graph)
    module = get_engine(engine)

    from gigi import __version__

    result = RunResult(
        run_id=uuid.uuid4().hex[:12],
        algorithm_id=spec.id,
        gigi_version=__version__,
        engine=engine,
        engine_version=module.version() if module.available() else None,
        dataset_id=data.id,
        requested_parameters=dict(parameters or {}),
    )

    if not module.available():
        result.status = RunStatus.unavailable
        result.error = f"{engine} is not installed"
        return result

    if not registry.has_implementation(spec.id, engine):
        result.status = RunStatus.unsupported
        result.error = f"{spec.id} has no {engine} implementation"
        return result

    params = resolve_parameters(spec, data, parameters)
    result.requested_parameters = params
    result.graph_profile = profile_graph(data)

    try:
        started = time.perf_counter()
        converted = module.convert(data)
        result.conversion_duration_ms = (time.perf_counter() - started) * 1000
        result.warnings.extend(converted.notes)

        implementation = registry.load_implementation(spec.id, engine)
        started = time.perf_counter()
        payload, effective = implementation.run(converted, params)
        result.execution_duration_ms = (time.perf_counter() - started) * 1000
        result.effective_parameters = dict(effective)

        started = time.perf_counter()
        result.result = normalize_node_score(
            payload, converted.node_ids, spec.output.score_name or "score"
        )
        result.normalization_duration_ms = (time.perf_counter() - started) * 1000

        # The maths, executed. Every property the spec claims is asserted here,
        # on every engine and every fixture -- which is what stops `maths:`
        # from being decoration.
        result.invariants = check_all(result.result, spec.maths.invariants)
    except Exception as exc:  # engines fail in engine-specific ways
        result.status = RunStatus.error
        result.error = f"{type(exc).__name__}: {exc}"

    return result


def compare(
    algorithm: str | AlgorithmSpec,
    graph: str | GraphData,
    engines: list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    explicit: bool = True,
    baseline: str = REFERENCE,
    allow_frontier: bool = False,
) -> tuple[list[RunResult], list[Comparison]]:
    """Run every engine on one graph and compare each against the baseline."""
    spec = _load(algorithm)
    check_runnable(spec, allow_frontier)
    data = _load_graph(graph)
    params = resolve_parameters(spec, data, parameters, explicit=explicit)

    candidates = engines or runnable_engines(spec)
    runs = [run(spec, engine, data, params, allow_frontier=True) for engine in candidates]
    by_engine = {r.engine: r for r in runs}

    comparisons: list[Comparison] = []
    reference_run = by_engine.get(baseline)
    if reference_run is None or reference_run.result is None:
        return runs, comparisons

    for candidate in runs:
        if candidate.engine == baseline or candidate.result is None:
            continue
        comparisons.append(
            compare_results(
                spec,
                data.id,
                baseline,
                reference_run.result,
                candidate.engine,
                candidate.result,
            )
        )
    return runs, comparisons


def runnable_engines(spec: AlgorithmSpec) -> list[str]:
    """Engines that are both installed and implemented for this algorithm."""
    return [
        engine
        for engine in available_engines()
        if registry.has_implementation(spec.id, engine)
    ]


def verify(
    algorithm: str | AlgorithmSpec,
    datasets: list[str] | None = None,
    engines: list[str] | None = None,
    allow_frontier: bool = False,
) -> VerificationReport:
    """The registry's claims, checked against reality.

    Two independent questions, deliberately not mixed:

    1. With every ambiguous parameter pinned, do the engines agree? Any
       disagreement must be named by a declared divergence, or verification
       fails.
    2. Does each declared divergence still reproduce under the conditions the
       registry says it reproduces under? A divergence that stopped happening
       is stale documentation, and verification fails.
    """
    spec = _load(algorithm)
    # Checked once here so the refusal is immediate and legible, rather than
    # arriving from inside a loop over fixtures.
    check_runnable(spec, allow_frontier)
    candidates = engines or runnable_engines(spec)
    dataset_ids = datasets or spec.datasets

    from gigi import __version__

    report = VerificationReport(
        algorithm_id=spec.id,
        gigi_version=__version__,
        engines=candidates,
        engine_versions={k: v for k, v in engine_versions().items() if k in candidates},
    )

    for dataset_id in dataset_ids:
        data = load_graph(dataset_id)
        runs, comparisons = compare(
            spec, data, engines=candidates, explicit=True, allow_frontier=True
        )
        report.runs.extend(runs)
        report.comparisons.extend(comparisons)

        for broken in (r for r in runs if r.failed_invariants):
            first = broken.failed_invariants[0]
            known = _explaining_divergence(spec, dataset_id, broken.engine)
            difference = Difference(
                dataset_id=dataset_id,
                engine_a="reference",
                engine_b=broken.engine,
                divergence_id=known,
                detail=f"violated {first.invariant_id}: {first.detail}",
            )
            if known:
                # The registry already says this engine misbehaves here -- an
                # invariant failure is one more way of seeing the same thing.
                report.explained_differences.append(difference)
            else:
                report.status = "fail"
                report.undeclared_differences.append(difference)
                report.conclusion = (
                    f"{broken.engine} violated {first.invariant_id} on {dataset_id}: "
                    f"{first.detail}"
                )

        for failed in (r for r in runs if r.status == RunStatus.error):
            known = _explaining_divergence(spec, dataset_id, failed.engine)
            difference = Difference(
                dataset_id=dataset_id,
                engine_a="reference",
                engine_b=failed.engine,
                divergence_id=known,
                detail=failed.error or "run failed",
            )
            if known:
                # The registry already says this engine cannot run here.
                report.explained_differences.append(difference)
            else:
                report.undeclared_differences.append(difference)
                report.conclusion = f"{failed.engine} failed on {dataset_id}: {failed.error}"

        for comparison in comparisons:
            if comparison.equivalent:
                continue
            difference = Difference(
                dataset_id=dataset_id,
                engine_a=comparison.engine_a,
                engine_b=comparison.engine_b,
                metrics=comparison.metrics,
                detail="; ".join(comparison.notes) or "results differ beyond tolerance",
            )
            known = _explaining_divergence(spec, dataset_id, comparison.engine_b)
            if known:
                difference.divergence_id = known
                report.explained_differences.append(difference)
            else:
                report.undeclared_differences.append(difference)

    report.divergence_checks.extend(_check_divergences(spec, candidates))

    if report.undeclared_differences:
        report.status = "fail"
    if any(not check.reproduced and check.observed != "skipped" for check in report.divergence_checks):
        report.status = "fail"

    if not report.conclusion:
        report.conclusion = _conclude(report)
    return report


def _explaining_divergence(spec: AlgorithmSpec, dataset_id: str, engine: str) -> str | None:
    for divergence in spec.divergences:
        detect = divergence.detect
        if detect and dataset_id in detect.datasets and engine in detect.engines:
            return divergence.id
    return None


def _check_divergences(spec: AlgorithmSpec, candidates: list[str]) -> list[DivergenceCheck]:
    """Re-run every declared divergence. One check per divergence, across every
    fixture it names -- the claim reproduces only if it holds on all of them."""
    checks: list[DivergenceCheck] = []
    for divergence in spec.divergences:
        detect = divergence.detect
        if detect is None:
            continue

        check = DivergenceCheck(
            divergence_id=divergence.id,
            datasets=detect.datasets,
            engines=detect.engines,
            expected=detect.expect,
            observed="skipped",
            reproduced=False,
        )
        missing = [engine for engine in detect.engines if engine not in candidates]
        if missing or len(detect.engines) != 2:
            check.note = (
                f"skipped: {', '.join(missing)} unavailable"
                if missing
                else "detect.engines must name exactly two engines"
            )
            checks.append(check)
            continue

        outcomes = {
            dataset_id: _observe(spec, detect, dataset_id)
            for dataset_id in detect.datasets
        }
        elsewhere = {d: o for d, o in outcomes.items() if o[0] != detect.expect}

        first_dataset = detect.datasets[0]
        check.observed = outcomes[first_dataset][0]
        check.metrics = outcomes[first_dataset][1]
        check.reproduced = not elsewhere and check.observed != "skipped"

        if elsewhere:
            check.note = "; ".join(
                f"{dataset}: expected {detect.expect}, observed {observed}"
                for dataset, (observed, _) in elsewhere.items()
            )
        elif len(detect.datasets) > 1:
            check.note = f"reproduced on all {len(detect.datasets)} fixtures"
        checks.append(check)
    return checks


def _observe(
    spec: AlgorithmSpec, detect, dataset_id: str
) -> tuple[str, dict[str, float]]:
    """What actually happens when the two engines meet this fixture."""
    first, second = detect.engines
    runs, comparisons = compare(
        spec,
        load_graph(dataset_id),
        engines=[first, second],
        parameters=detect.parameters,
        explicit=False,
        baseline=first,
        allow_frontier=True,
    )
    subject = next((r for r in runs if r.engine == second), None)

    if subject is not None and subject.status == RunStatus.error:
        return "error", {}
    if comparisons:
        comparison = comparisons[0]
        return ("match" if comparison.equivalent else "differ"), comparison.metrics
    return "skipped", {}


def _conclude(report: VerificationReport) -> str:
    engines = ", ".join(report.engines)
    if report.status == "pass":
        reproduced = sum(1 for c in report.divergence_checks if c.reproduced)
        return (
            f"{len(report.runs)} runs across {engines}; engines agree wherever the "
            f"registry says they should; {reproduced} declared divergence(s) reproduced"
        )
    return (
        f"{len(report.undeclared_differences)} undeclared difference(s) and "
        f"{sum(1 for c in report.divergence_checks if not c.reproduced and c.observed != 'skipped')} "
        f"unreproduced divergence claim(s)"
    )
