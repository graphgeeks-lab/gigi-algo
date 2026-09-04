"""The generalised schema: kinds, discriminated inputs, domains.

PR 1 made the schema stop being graph-shaped; PR 2b put a non-graph method in
it. These are the checks that keep the generality honest — and, more usefully,
the ones that stop a general schema drifting into a shape that fits everything
and helps with nothing. Every extension point here has a price, in the same
spirit as *an invariant must name a check*.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from gigi import registry
from gigi.models import (
    GraphInputSpec,
    InputSpec,
    MethodKind,
    OutputKind,
    VectorInputSpec,
)
from gigi.results import COMPARATORS

METHODS = registry.list_methods()
INPUTS = TypeAdapter(InputSpec)


# --- kinds ------------------------------------------------------------------


@pytest.mark.parametrize("method_id", METHODS)
def test_every_method_declares_a_kind(method_id):
    spec = registry.load_method(method_id)
    assert isinstance(spec.kind, MethodKind)


def test_no_method_kind_is_unused_speculation():
    """A kind exists because a method needed it, never in advance.

    Two so far: `algorithm` for the graph entries, and `measure`, which arrived
    with cosine similarity. `statistical_model`, `heuristic`, `procedure` and
    `solver` are named in the enum and unused, which is the enum's job -- but
    the moment one of them is used, this test says so, and the reviewer gets to
    ask whether the entry really needed a new kind.
    """
    used = {registry.load_method(m).kind for m in METHODS}
    assert used == {MethodKind.algorithm, MethodKind.measure}, (
        f"method kinds in use: {sorted(k.value for k in used)}. A new kind is a "
        f"claim that verifying this thing means something different; say so in "
        f"the PR and update this test."
    )


# --- inputs: the union has to actually discriminate -------------------------


def test_graph_input_is_selected_by_its_kind():
    parsed = INPUTS.validate_python(
        {"kind": "graph", "directed": {"supported": True},
         "weighted": {"supported": False}, "negative_weights": {"supported": False}}
    )
    assert isinstance(parsed, GraphInputSpec)


def test_vector_input_is_selected_by_its_kind():
    """The union is discriminated, not a union of one -- and since PR 2b the
    `vectors` branch has a method behind it rather than only a test."""
    parsed = INPUTS.validate_python({"kind": "vectors", "numeric": True})
    assert isinstance(parsed, VectorInputSpec)
    assert parsed.same_length_required is True


def test_an_unknown_input_kind_is_rejected():
    with pytest.raises(ValidationError, match="kind"):
        INPUTS.validate_python({"kind": "point_cloud"})


def test_a_graph_input_cannot_borrow_vector_fields():
    """Discrimination means a graph author never has to think about vectors,
    and cannot accidentally fill one in."""
    with pytest.raises(ValidationError):
        GraphInputSpec.model_validate(
            {"kind": "graph", "directed": {"supported": True},
             "weighted": {"supported": True}, "negative_weights": {"supported": False},
             "numeric": True}
        )


@pytest.mark.parametrize("method_id", METHODS)
def test_every_method_declares_at_least_one_input(method_id):
    spec = registry.load_method(method_id)
    assert spec.inputs, f"{method_id} consumes nothing"


# --- outputs: the rule with teeth -------------------------------------------


@pytest.mark.parametrize("kind", list(OutputKind))
def test_every_output_kind_has_a_comparator(kind):
    """The extension rule from docs/ONTOLOGY.md, enforced.

    An output kind with no comparator describes a method nothing can verify.
    Adding `similarity_score` to the enum without writing the comparator that
    judges two similarity scores should fail here, loudly, before any method
    can claim it.
    """
    assert kind in COMPARATORS, (
        f"output kind {kind.value!r} has no comparator in gigi/results.py. "
        f"Write the comparator, or do not add the kind."
    )


@pytest.mark.parametrize("method_id", METHODS)
def test_method_output_kind_is_comparable(method_id):
    assert registry.load_method(method_id).output.kind in COMPARATORS


# --- domains ----------------------------------------------------------------


def test_domains_exist():
    assert registry.list_domains()


@pytest.mark.parametrize("family_id", [f.id for f in registry.list_families()])
def test_every_family_belongs_to_a_real_domain(family_id):
    family = registry.load_family(family_id)
    assert registry.domain_exists(family.domain), (
        f"family {family_id} is in domain {family.domain!r}, which is not in "
        f"domains/domains.yaml"
    )


@pytest.mark.parametrize("domain_id", [d.id for d in registry.list_domains()])
def test_no_domain_is_empty(domain_id):
    """A domain earns its place by having a family in it. An empty domain is a
    plan, and plans belong in PLAN.md."""
    assert registry.families_in_domain(domain_id), (
        f"domain {domain_id!r} has no families; it is a roadmap entry, not a domain"
    )


@pytest.mark.parametrize("method_id", METHODS)
def test_a_methods_domain_is_derived_not_stored(method_id):
    """There is one path from method to domain, through the family. If the
    method carried its own `domain` the two could disagree; it cannot."""
    spec = registry.load_method(method_id)
    assert not hasattr(spec, "domain"), "domain is derived, never stored on the method"
    assert registry.domain_of(spec) == registry.load_family(spec.family).domain


def test_methods_can_be_grouped_by_domain():
    """Two domains with content in them, which is the whole claim of the
    generalisation: the same registry holds a graph algorithm and a vector
    measure, and neither is a special case of the other."""
    graph_methods = registry.methods_in_domain("graph")
    similarity_methods = registry.methods_in_domain("similarity")

    assert "pagerank" in graph_methods
    assert "cosine_similarity" in similarity_methods
    assert not set(graph_methods) & set(similarity_methods)
    assert sorted([*graph_methods, *similarity_methods]) == METHODS


def test_unknown_domain_names_the_ones_that_exist():
    with pytest.raises(registry.RegistryError, match="graph"):
        registry.load_domain("astrophysics")
