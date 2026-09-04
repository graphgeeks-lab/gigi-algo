"""Run, compare, verify.

Three functions. The CLI, the Python API and any future agent tool call these
same three -- there is no second code path.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from gigi import registry
from gigi.backends import available_backends, backend_versions, get_backend
from gigi.data import Dataset, load_dataset, profile_dataset
from gigi.graph import GraphData
from gigi.models import (
    MethodSpec,
    Comparison,
    Difference,
    DivergenceCheck,
    RunResult,
    RunStatus,
    VerificationReport,
)
from gigi.invariants import CheckContext, check_all
from gigi.maturity import check_runnable
from gigi.results import compare_results, normalize

REFERENCE = "reference"

# `weight_property` is tri-state and that is the point:
#   None   -> let the backend apply its own default (which is what diverges)
#   False  -> explicitly unweighted
#   "name" -> use this edge attribute
WEIGHT_PROPERTY = "weight_property"


def default_parameters(spec: MethodSpec) -> dict[str, Any]:
    """What a caller gets when they ask for nothing: Gigi's canonical defaults
    where the community agrees on one, and the backend's own default everywhere
    else. This is the configuration under which backends disagree."""
    return {p.name: p.common_default for p in spec.parameters}


def explicit_parameters(spec: MethodSpec, data: Dataset) -> dict[str, Any]:
    """Every ambiguous parameter pinned, so that any remaining disagreement is
    a real semantic difference rather than a difference of defaults.

    Tolerances and caps come from `verification.parameters` in the spec;
    `weight_property` is derived from the dataset because only the dataset
    knows whether there is a weight column to use.
    """
    params = default_parameters(spec)
    params.update(spec.verification.parameters)
    # Only a graph has a weight column. A method whose input is not a graph
    # never declares the parameter, so this is a guard rather than a branch
    # anyone has to think about.
    if WEIGHT_PROPERTY in params and isinstance(data, GraphData):
        params[WEIGHT_PROPERTY] = data.weight_column or False
    return params


def resolve_parameters(
    spec: MethodSpec,
    data: Dataset,
    overrides: dict[str, Any] | None = None,
    explicit: bool = False,
) -> dict[str, Any]:
    """Canonical parameters for one run: defaults, then pinned values if
    `explicit`, then whatever the caller asked for."""
    params = explicit_parameters(spec, data) if explicit else default_parameters(spec)
    params.update(overrides or {})
    return params


def _load(algorithm: str | MethodSpec) -> MethodSpec:
    return algorithm if isinstance(algorithm, MethodSpec) else registry.load_method(algorithm)


def _load_data(dataset: str | Dataset) -> Dataset:
    """A dataset id, or an already-loaded dataset of whatever kind."""
    return load_dataset(dataset) if isinstance(dataset, str) else dataset


def run(
    algorithm: str | MethodSpec,
    backend: str,
    dataset: str | Dataset,
    parameters: dict[str, Any] | None = None,
    allow_frontier: bool = False,
) -> RunResult:
    """Execute one algorithm on one backend and return a fully described run.

    An *backend* failure is a RunResult with a status, never an exception:
    verification needs to report what did not run as much as what did. A
    *policy* refusal is different -- a frontier algorithm without opt-in raises
    `FrontierBlocked`, because there is no result to describe and the caller
    asked for something they are not allowed to have.
    """
    spec = _load(algorithm)
    check_runnable(spec, allow_frontier)
    data = _load_data(dataset)
    module = get_backend(backend)

    from gigi import __version__

    result = RunResult(
        run_id=uuid.uuid4().hex[:12],
        method_id=spec.id,
        gigi_version=__version__,
        backend=backend,
        backend_version=module.version() if module.available() else None,
        dataset_id=data.id,
        requested_parameters=dict(parameters or {}),
    )

    if not module.available():
        result.status = RunStatus.unavailable
        result.error = f"{backend} is not installed"
        return result

    if not registry.has_implementation(spec.id, backend):
        result.status = RunStatus.unsupported
        result.error = f"{spec.id} has no {backend} implementation"
        return result

    params = resolve_parameters(spec, data, parameters)
    result.requested_parameters = params
    result.profile = profile_dataset(data)

    try:
        started = time.perf_counter()
        converted = module.convert(data)
        result.conversion_duration_ms = (time.perf_counter() - started) * 1000
        result.warnings.extend(converted.notes)

        implementation = registry.load_implementation(spec.id, backend)
        started = time.perf_counter()
        payload, effective = implementation.run(converted, params)
        result.execution_duration_ms = (time.perf_counter() - started) * 1000
        result.effective_parameters = dict(effective)

        started = time.perf_counter()
        result.result = normalize(
            payload,
            converted.result_keys,
            spec.output,
            require_all_keys=converted.keys_are_complete,
        )
        result.normalization_duration_ms = (time.perf_counter() - started) * 1000

        # The maths, executed. Every property the spec claims is asserted here,
        # on every backend and every fixture -- which is what stops `maths:`
        # from being decoration. The dataset goes too: "every component is
        # connected" is a claim about the result *and* the graph it came from.
        result.invariants = check_all(
            result.result,
            spec.maths.invariants,
            CheckContext(data=data, parameters=result.effective_parameters),
        )
    except Exception as exc:  # backends fail in backend-specific ways
        result.status = RunStatus.error
        result.error = f"{type(exc).__name__}: {exc}"

    return result


def compare(
    algorithm: str | MethodSpec,
    dataset: str | Dataset,
    backends: list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    explicit: bool = True,
    baseline: str = REFERENCE,
    allow_frontier: bool = False,
) -> tuple[list[RunResult], list[Comparison]]:
    """Run every backend on one dataset and compare each against the baseline."""
    spec = _load(algorithm)
    check_runnable(spec, allow_frontier)
    data = _load_data(dataset)
    params = resolve_parameters(spec, data, parameters, explicit=explicit)

    candidates = backends or runnable_backends(spec)
    runs = [run(spec, backend, data, params, allow_frontier=True) for backend in candidates]
    by_engine = {r.backend: r for r in runs}

    comparisons: list[Comparison] = []
    reference_run = by_engine.get(baseline)
    if reference_run is None or reference_run.result is None:
        return runs, comparisons

    for candidate in runs:
        if candidate.backend == baseline or candidate.result is None:
            continue
        comparisons.append(
            compare_results(
                spec,
                data.id,
                baseline,
                reference_run.result,
                candidate.backend,
                candidate.result,
            )
        )
    return runs, comparisons


def runnable_backends(spec: MethodSpec) -> list[str]:
    """Backends that are both installed and implemented for this algorithm."""
    return [
        backend
        for backend in available_backends()
        if registry.has_implementation(spec.id, backend)
    ]


def verify(
    algorithm: str | MethodSpec,
    datasets: list[str] | None = None,
    backends: list[str] | None = None,
    allow_frontier: bool = False,
) -> VerificationReport:
    """The registry's claims, checked against reality.

    Two independent questions, deliberately not mixed:

    1. With every ambiguous parameter pinned, do the backends agree? Any
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
    candidates = backends or runnable_backends(spec)
    dataset_ids = datasets or spec.datasets

    from gigi import __version__

    report = VerificationReport(
        method_id=spec.id,
        gigi_version=__version__,
        backends=candidates,
        backend_versions={k: v for k, v in backend_versions().items() if k in candidates},
    )

    for dataset_id in dataset_ids:
        data = load_dataset(dataset_id)
        runs, comparisons = compare(
            spec, data, backends=candidates, explicit=True, allow_frontier=True
        )
        report.runs.extend(runs)
        report.comparisons.extend(comparisons)

        for broken in (r for r in runs if r.failed_invariants):
            first = broken.failed_invariants[0]
            known = _explaining_divergence(spec, dataset_id, broken.backend)
            difference = Difference(
                dataset_id=dataset_id,
                backend_a="reference",
                backend_b=broken.backend,
                divergence_id=known,
                detail=f"violated {first.invariant_id}: {first.detail}",
            )
            if known:
                # The registry already says this backend misbehaves here -- an
                # invariant failure is one more way of seeing the same thing.
                report.explained_differences.append(difference)
            else:
                report.status = "fail"
                report.undeclared_differences.append(difference)
                report.conclusion = (
                    f"{broken.backend} violated {first.invariant_id} on {dataset_id}: "
                    f"{first.detail}"
                )

        for failed in (r for r in runs if r.status == RunStatus.error):
            known = _explaining_divergence(spec, dataset_id, failed.backend)
            difference = Difference(
                dataset_id=dataset_id,
                backend_a="reference",
                backend_b=failed.backend,
                divergence_id=known,
                detail=failed.error or "run failed",
            )
            if known:
                # The registry already says this backend cannot run here.
                report.explained_differences.append(difference)
            else:
                report.undeclared_differences.append(difference)
                report.conclusion = f"{failed.backend} failed on {dataset_id}: {failed.error}"

        for comparison in comparisons:
            if comparison.equivalent:
                continue
            difference = Difference(
                dataset_id=dataset_id,
                backend_a=comparison.backend_a,
                backend_b=comparison.backend_b,
                metrics=comparison.metrics,
                detail="; ".join(comparison.notes) or "results differ beyond tolerance",
            )
            known = _explaining_divergence(spec, dataset_id, comparison.backend_b)
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


def _explaining_divergence(spec: MethodSpec, dataset_id: str, backend: str) -> str | None:
    for divergence in spec.divergences:
        detect = divergence.detect
        if detect and dataset_id in detect.datasets and backend in detect.backends:
            return divergence.id
    return None


def _check_divergences(spec: MethodSpec, candidates: list[str]) -> list[DivergenceCheck]:
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
            backends=detect.backends,
            expected=detect.expect,
            observed="skipped",
            reproduced=False,
        )
        missing = [backend for backend in detect.backends if backend not in candidates]
        if missing or len(detect.backends) != 2:
            check.note = (
                f"skipped: {', '.join(missing)} unavailable"
                if missing
                else "detect.backends must name exactly two backends"
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
    spec: MethodSpec, detect, dataset_id: str
) -> tuple[str, dict[str, float]]:
    """What actually happens when the two backends meet this fixture."""
    first, second = detect.backends
    runs, comparisons = compare(
        spec,
        load_dataset(dataset_id),
        backends=[first, second],
        parameters=detect.parameters,
        explicit=False,
        baseline=first,
        allow_frontier=True,
    )
    subject = next((r for r in runs if r.backend == second), None)

    if subject is not None and subject.status == RunStatus.error:
        return "error", {}
    if comparisons:
        comparison = comparisons[0]
        return ("match" if comparison.equivalent else "differ"), comparison.metrics
    return "skipped", {}


def _conclude(report: VerificationReport) -> str:
    backends = ", ".join(report.backends)
    if report.status == "pass":
        reproduced = sum(1 for c in report.divergence_checks if c.reproduced)
        return (
            f"{len(report.runs)} runs across {backends}; backends agree wherever the "
            f"registry says they should; {reproduced} declared divergence(s) reproduced"
        )
    return (
        f"{len(report.undeclared_differences)} undeclared difference(s) and "
        f"{sum(1 for c in report.divergence_checks if not c.reproduced and c.observed != 'skipped')} "
        f"unreproduced divergence claim(s)"
    )
