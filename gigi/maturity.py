"""The maturity contract, enforced rather than labelled.

`frontier` means "we are not yet standing behind this". A tier that only
appears in a table is decoration: the whole point is that a frontier
implementation must never be run by accident, and never be selected by an
agent that was simply asking for the best available algorithm.

So the gate lives here, at the harness boundary, not in the CLI. Every caller
inherits it: the Python API, the CLI, and any future agent tool. Opting in is
deliberate and per-call:

    gigi run my_algorithm --graph tiny-directed --allow-frontier
    GIGI_ALLOW_FRONTIER=1 gigi verify my_algorithm      # a whole session
    gigi.run("my_algorithm", ..., allow_frontier=True)  # in code

`historical` is *not* gated. It is frozen, not dangerous: it runs, and the
registry simply stops recommending it.
"""

from __future__ import annotations

import os

from gigi.models import MethodSpec, Maturity

FRONTIER_ENV = "GIGI_ALLOW_FRONTIER"
_TRUE = {"1", "true", "yes", "on"}


class FrontierBlocked(RuntimeError):
    """A frontier algorithm was asked to run without explicit opt-in."""


def frontier_allowed(explicit: bool = False) -> bool:
    """Has the caller opted in, by argument or by environment?"""
    return explicit or os.environ.get(FRONTIER_ENV, "").strip().lower() in _TRUE


def gated(spec: MethodSpec) -> bool:
    """Does this algorithm need an opt-in before it will run?"""
    return spec.maturity is Maturity.frontier


def check_runnable(spec: MethodSpec, allow_frontier: bool = False) -> None:
    """Raise unless this algorithm may run under the current policy."""
    if gated(spec) and not frontier_allowed(allow_frontier):
        raise FrontierBlocked(
            f"{spec.id} is `frontier`: not verified, not stood behind, and never "
            f"run by accident. Opt in explicitly with --allow-frontier, or set "
            f"{FRONTIER_ENV}=1 for a session. See docs/MATURITY.md."
        )
