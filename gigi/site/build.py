"""Writing the site to disk."""

from __future__ import annotations

from pathlib import Path

from gigi import people, registry
from gigi.harness import verify
from gigi.maturity import FrontierBlocked
from gigi.models import MethodSpec, VerificationReport
from gigi.runstore import load_report
from gigi.site.html import INLINE, page
from gigi.site.pages import algorithm_body, index_body, person_body

def collect(verify_first: bool) -> tuple[list[MethodSpec], dict[str, VerificationReport]]:
    """Load every spec, and either run verification now or read the last report."""
    specs = [registry.load_method(a) for a in registry.list_methods()]
    reports: dict[str, VerificationReport] = {}
    for spec in specs:
        try:
            report = verify(spec) if verify_first else load_report(spec.id)
        except FrontierBlocked:
            # A frontier entry is published without evidence, which is the
            # honest thing to show: it has not been verified.
            continue
        if report:
            reports[spec.id] = report
    return specs, reports


def build_site(
    output: str | Path = "site", verify_first: bool = True, single_file: bool = False
) -> Path:
    """Write the site. `single_file` collapses it into one shareable document."""
    specs, reports = collect(verify_first)

    profiles = [people.profile(person.id) for person in people.list_people()]

    if single_file:
        path = Path(output)
        if path.is_dir() or not path.suffix:
            path = path / "gigi.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            index_body(specs, reports, INLINE)
            + "".join(
                algorithm_body(spec, reports.get(spec.id), INLINE, heading="h2")
                for spec in specs
            )
            + "".join(person_body(profile, INLINE, heading="h2") for profile in profiles)
        )
        path.write_text(page("Gigi — graph algorithm registry", body), encoding="utf-8")
        return path

    root = Path(output)
    (root / "algorithms").mkdir(parents=True, exist_ok=True)
    (root / "people").mkdir(parents=True, exist_ok=True)

    for spec in specs:
        (root / "algorithms" / f"{spec.id}.html").write_text(
            page(f"{spec.name} — Gigi", algorithm_body(spec, reports.get(spec.id))),
            encoding="utf-8",
        )
    for profile in profiles:
        (root / "people" / f"{profile.person.id}.html").write_text(
            page(f"{profile.person.name} — Gigi", person_body(profile)),
            encoding="utf-8",
        )

    index = root / "index.html"
    index.write_text(
        page("Gigi — graph algorithm registry", index_body(specs, reports)), encoding="utf-8"
    )
    return index
