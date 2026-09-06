"""Copy the version from pyproject.toml into CITATION.cff.

`uv version` edits pyproject.toml and nothing else, by design. CITATION.cff has
to carry the same number for the citation to be right, and it is the one file
that cannot read it at runtime. So: one script, one direction, no options.

    python scripts/sync-version.py           # write
    python scripts/sync-version.py --check   # exit 1 if they differ; CI uses this

No dependencies beyond the standard library, so it runs before anything is
installed.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CITATION = ROOT / "CITATION.cff"


def pyproject_version() -> str:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def citation_version(text: str) -> str | None:
    match = re.search(r"^version:\s*(\S+)\s*$", text, re.M)
    return match.group(1) if match else None


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    want = pyproject_version()
    text = CITATION.read_text(encoding="utf-8")
    have = citation_version(text)

    if have == want:
        print(f"CITATION.cff already says {want}")
        return 0
    if check_only:
        print(f"CITATION.cff says {have}, pyproject.toml says {want}. Run scripts/sync-version.py.")
        return 1

    text = re.sub(r"^version:\s*\S+\s*$", f"version: {want}", text, count=1, flags=re.M)
    today = dt.date.today().isoformat()
    if re.search(r"^date-released:", text, re.M):
        text = re.sub(r"^date-released:.*$", f"date-released: {today}", text, count=1, flags=re.M)
    else:
        text = text.replace(f"version: {want}\n", f"version: {want}\ndate-released: {today}\n", 1)
    CITATION.write_text(text, encoding="utf-8")
    print(f"CITATION.cff: {have} -> {want} (date-released {today})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
