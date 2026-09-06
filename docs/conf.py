"""Sphinx configuration for the human-facing Gigi handbook."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gigi

project = "Gigi"
copyright = "2026, GraphGeeks Labs"
author = "Dennis Irorere"
version = gigi.__version__
release = gigi.__version__

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinxcontrib.mermaid",
]
source_suffix = {".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build"]
myst_heading_anchors = 3
myst_fence_as_directive = ["mermaid"]
autodoc_typehints = "description"

# GraphFaker uses Sphinx's built-in Alabaster theme. Keeping the same theme
# makes this a small, dependency-light Read the Docs build.
html_theme = "alabaster"
html_title = f"Gigi {version}"
html_static_path: list[str] = []
