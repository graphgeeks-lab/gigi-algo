"""The maturity contract has teeth, or it is decoration.

`frontier` must refuse to run without an explicit opt-in, from every entry
point; promotion must refuse an entry that has not earned the tier. Both are
tested against a throwaway registry rather than the real one, so the checks
exist before there is a frontier algorithm to trip over them.
"""

from __future__ import annotations

import shutil

import pytest

from gigi import maturity, registry, requirements
from gigi.harness import compare, run, verify
from gigi.maturity import FrontierBlocked
from gigi.models import Maturity
from gigi.paths import algorithms_dir

FRONTIER_ID = "frontier_check"
EMERGING_ID = "emerging_check"


def _registry_with(tmp_path, monkeypatch, algorithm_id: str, tier: str):
    """A registry holding one copy of degree_centrality at the given tier."""
    root = tmp_path / "algorithms"
    destination = root / algorithm_id
    shutil.copytree(algorithms_dir() / "degree_centrality", destination)

    spec_path = destination / "algorithm.yaml"
    text = spec_path.read_text(encoding="utf-8")
    text = text.replace("id: degree_centrality", f"id: {algorithm_id}", 1)
    text = text.replace("maturity: emerging", f"maturity: {tier}", 1)
    spec_path.write_text(text, encoding="utf-8")

    monkeypatch.setenv("GIGI_ALGORITHMS_DIR", str(root))
    monkeypatch.delenv(maturity.FRONTIER_ENV, raising=False)
    registry.load_algorithm.cache_clear()
    yield_id = algorithm_id
    return yield_id


@pytest.fixture()
def frontier(tmp_path, monkeypatch):
    algorithm_id = _registry_with(tmp_path, monkeypatch, FRONTIER_ID, "frontier")
    yield algorithm_id
    registry.load_algorithm.cache_clear()


@pytest.fixture()
def emerging(tmp_path, monkeypatch):
    algorithm_id = _registry_with(tmp_path, monkeypatch, EMERGING_ID, "emerging")
    yield algorithm_id
    registry.load_algorithm.cache_clear()


# --- the gate ---------------------------------------------------------------


def test_run_refuses_a_frontier_algorithm(frontier):
    with pytest.raises(FrontierBlocked, match="frontier"):
        run(frontier, "reference", "tiny-directed")


def test_compare_and_verify_refuse_too(frontier):
    """Every entry point, not just the obvious one -- the gate is in the
    harness so that anything calling it inherits the refusal."""
    with pytest.raises(FrontierBlocked):
        compare(frontier, "tiny-directed")
    with pytest.raises(FrontierBlocked):
        verify(frontier)


def test_the_refusal_says_how_to_opt_in(frontier):
    with pytest.raises(FrontierBlocked) as raised:
        run(frontier, "reference", "tiny-directed")
    message = str(raised.value)
    assert "--allow-frontier" in message
    assert maturity.FRONTIER_ENV in message
    assert "docs/MATURITY.md" in message


def test_explicit_opt_in_lets_it_run(frontier):
    result = run(frontier, "reference", "tiny-directed", allow_frontier=True)
    assert result.status.value == "ok"
    assert result.result.scores


def test_environment_opt_in_lets_it_run(frontier, monkeypatch):
    monkeypatch.setenv(maturity.FRONTIER_ENV, "1")
    assert run(frontier, "reference", "tiny-directed").status.value == "ok"
    assert verify(frontier).status in {"pass", "fail"}


@pytest.mark.parametrize("value,expected", [("1", True), ("true", True), ("YES", True),
                                            ("0", False), ("", False), ("maybe", False)])
def test_environment_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv(maturity.FRONTIER_ENV, value)
    assert maturity.frontier_allowed() is expected


def test_only_frontier_is_gated(emerging):
    """`historical` is frozen, not dangerous; `emerging` and `stable` run."""
    assert run(emerging, "reference", "tiny-directed").status.value == "ok"
    spec = registry.load_algorithm(emerging)
    for tier in (Maturity.emerging, Maturity.stable, Maturity.historical):
        assert not maturity.gated(spec.model_copy(update={"maturity": tier}))
    assert maturity.gated(spec.model_copy(update={"maturity": Maturity.frontier}))


# --- promotion --------------------------------------------------------------


def test_promotion_refuses_a_tier_that_has_not_been_earned(frontier):
    """The frontier copy keeps degree_centrality's content, so it clears
    `emerging` -- but strip a requirement and promotion must refuse."""
    spec = registry.load_algorithm(frontier)
    directory = registry.algorithm_dir(frontier)
    (directory / "tests" / "expected.yaml").unlink()

    from gigi.knownanswers import load_cases

    load_cases.cache_clear()
    lacking = [
        o for o in requirements.check(spec)
        if not o.met and requirements.RANK[o.requirement.mandatory_from]
        <= requirements.RANK[Maturity.emerging]
    ]
    assert any("known-answer" in o.requirement.description for o in lacking)
    load_cases.cache_clear()


def test_set_maturity_rewrites_the_spec_and_nothing_else(emerging):
    before = (registry.algorithm_dir(emerging) / "algorithm.yaml").read_text(encoding="utf-8")
    registry.set_maturity(emerging, Maturity.stable)
    after = (registry.algorithm_dir(emerging) / "algorithm.yaml").read_text(encoding="utf-8")

    assert registry.load_algorithm(emerging).maturity is Maturity.stable
    changed = [
        (a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b
    ]
    assert changed == [("maturity: emerging", "maturity: stable")], (
        "promotion must touch the maturity line and nothing else"
    )


def test_next_tier_names_the_rung_above(emerging):
    target, _ = requirements.next_tier(registry.load_algorithm(emerging))
    assert target is Maturity.stable


def test_real_registry_has_no_ungated_surprises():
    """Whatever is in the registry today, every entry declares a tier we know
    how to enforce."""
    for algorithm_id in registry.list_algorithms():
        spec = registry.load_algorithm(algorithm_id)
        assert spec.maturity in requirements.RANK
