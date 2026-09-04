"""The review summary has to be honest about what it did and did not settle."""

from __future__ import annotations

from gigi.review import review


def test_review_passes_for_a_healthy_algorithm():
    result = review("pagerank")
    assert result.ok, [f"{c.name}: {c.detail}" for c in result.failed]


def test_review_covers_the_requirements_of_the_claimed_tier():
    """Every requirement binding at this maturity appears as a settled check,
    alongside the four things that only running the algorithm can settle."""
    from gigi import registry, requirements

    spec = registry.load_method("pagerank")
    names = {check.name for check in review("pagerank").checks}
    for outcome in requirements.check(spec):
        if outcome.required:
            assert outcome.requirement.description in names
    for expected in (
        "reference gives every known answer",
        "backends agree where the registry says they agree",
        "invariants hold on every run, or the failure is a declared divergence",
        "declared divergences still reproduce",
    ):
        assert expected in names, f"review no longer checks {expected!r}"


def test_review_names_the_path_to_promotion():
    target, lacking = review("degree_centrality").promotion
    assert target == "stable"
    assert all(":" in item for item in lacking), "each item names the requirement and the gap"


def test_by_eye_list_stays_short():
    """A checklist nobody finishes protects nothing."""
    items = review("pagerank").by_eye
    assert 3 <= len(items) <= 8, f"{len(items)} by-eye items is too many to finish"


def test_the_oracle_question_comes_first():
    """If the reference implementation is wrong, every automated check above it
    is meaningless -- so it leads."""
    first = review("pagerank").by_eye[0]
    assert "reference implementation" in first.question.lower()
    assert "reference.py" in first.where


def test_gaps_are_reported_but_do_not_fail_the_review():
    result = review("pagerank")
    assert result.ok
    # pagerank has a choice point with no fixture; that is a gap, not a failure.
    assert result.gaps
