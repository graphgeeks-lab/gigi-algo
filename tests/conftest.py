"""Shared fixtures and the one policy the test suite has to respect.

`frontier` entries are not verified and are not run by accident — including
here. The suites that *execute* algorithms skip them unless the same opt-in
the harness wants is present; the suites that only *read* the registry
(schema, attribution, taxonomy) still cover them, because those checks are
cheap and must hold for every entry.

That mirrors the maturity contract: frontier gets schema validation and a
smoke run, not blocking conformance. See docs/MATURITY.md.
"""

from __future__ import annotations

from gigi import registry
from gigi.maturity import frontier_allowed, gated


def executable_algorithms() -> list[str]:
    """Algorithms the suite may run right now."""
    return [
        method_id
        for method_id in registry.list_methods()
        if frontier_allowed() or not gated(registry.load_method(method_id))
    ]
