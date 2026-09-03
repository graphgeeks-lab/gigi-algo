"""Local run state as JSON files under `.gigi/`.

No database. `gigi verify --last-run` needs to remember one thing, and a
directory of JSON does that while staying inspectable with `cat`.
"""

from __future__ import annotations

import json
from pathlib import Path

from gigi.models import RunResult, VerificationReport
from gigi.paths import state_dir


def _dir(name: str) -> Path:
    path = state_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_run(result: RunResult) -> Path:
    """Write one run and point `last_run` at it."""
    path = _dir("runs") / f"{result.run_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (state_dir() / "last_run.json").write_text(
        json.dumps({"run_id": result.run_id}), encoding="utf-8"
    )
    return path


def last_run() -> RunResult | None:
    """The most recent run, or None if nothing has run in this directory."""
    pointer = state_dir() / "last_run.json"
    if not pointer.is_file():
        return None
    run_id = json.loads(pointer.read_text(encoding="utf-8"))["run_id"]
    path = state_dir() / "runs" / f"{run_id}.json"
    if not path.is_file():
        return None
    return RunResult.model_validate_json(path.read_text(encoding="utf-8"))


def save_report(report: VerificationReport) -> Path:
    path = _dir("reports") / f"{report.algorithm_id}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(algorithm_id: str) -> VerificationReport | None:
    path = state_dir() / "reports" / f"{algorithm_id}.json"
    if not path.is_file():
        return None
    return VerificationReport.model_validate_json(path.read_text(encoding="utf-8"))
