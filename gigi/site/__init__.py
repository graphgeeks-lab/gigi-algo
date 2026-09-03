"""Render the registry, plus live verification evidence, as static HTML.

No framework, no JavaScript, no build step: `gigi site build` writes files that
GitHub Pages can serve directly. The site is a view over the same objects the
library returns, so it cannot drift from what the code actually does.

Four modules, in the order worth reading them:

    html.py       the page shell, the link scheme, and four primitives
    sections.py   one function per section of an algorithm page
    pages.py      whole documents: the index, an algorithm, a person
    build.py      writing them to disk
"""

from __future__ import annotations

from gigi.site.build import build_site

__all__ = ["build_site"]
