"""Readability, as a checked property.

Every other claim in this project is executable, and "the code is reviewable"
should not be the exception. These are the rules stated in PLAN.md and
CONTRIBUTING.md, enforced rather than hoped for:

- a module splits when it passes ~400 lines of code, not when someone
  remembers to;
- a reader landing in a file learns from its docstring what it is for;
- a public name that is not obvious explains itself.

The caps are deliberately generous. They exist to catch drift over months, not
to police individual functions -- a test that fires constantly gets suppressed,
and then protects nothing.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from gigi.paths import repo_root

MODULE_CODE_LINE_CAP = 400
FUNCTION_LINE_CAP = 120
TRIVIAL_FUNCTION_LINES = 5

PACKAGE = repo_root() / "gigi"
MODULES = sorted(PACKAGE.rglob("*.py"))


def _parsed(path: pathlib.Path) -> tuple[str, ast.Module]:
    source = path.read_text(encoding="utf-8")
    return source, ast.parse(source)


def _docstring_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text and node.body and isinstance(node.body[0], ast.Expr):
                first = node.body[0]
                lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines


def code_lines(path: pathlib.Path) -> int:
    """Lines that are neither blank, nor a comment, nor a docstring.

    Prose is not what makes a file hard to read, so it does not count against
    the budget. This is the same measure PLAN.md quotes.
    """
    source, tree = _parsed(path)
    skip = _docstring_lines(tree)
    return sum(
        1
        for number, line in enumerate(source.splitlines(), 1)
        if line.strip() and not line.strip().startswith("#") and number not in skip
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_module_is_small_enough_to_hold_in_your_head(path):
    count = code_lines(path)
    assert count <= MODULE_CODE_LINE_CAP, (
        f"{path.relative_to(repo_root())} is {count} code lines, over the "
        f"{MODULE_CODE_LINE_CAP} cap. Split it by concern -- the rule exists so "
        f"that a reviewer can read a whole file before judging a change to it."
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_module_says_what_it_is_for(path):
    _, tree = _parsed(path)
    docstring = ast.get_docstring(tree)
    assert docstring and docstring.strip(), (
        f"{path.relative_to(repo_root())} has no module docstring. Someone will "
        f"land here from a stack trace and need to know what this file is for."
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_public_names_explain_themselves(path):
    """A public function either is obvious from its body, or says what it does.

    Trivial functions are exempt: a five-line accessor explains itself, and a
    docstring on it is noise.
    """
    _, tree = _parsed(path)
    undocumented = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        if length <= TRIVIAL_FUNCTION_LINES:
            continue
        if not ast.get_docstring(node):
            undocumented.append(f"{node.name} (line {node.lineno}, {length} lines)")

    assert not undocumented, (
        f"{path.relative_to(repo_root())}: public names with no docstring: "
        f"{', '.join(undocumented)}"
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_no_function_is_a_wall(path):
    _, tree = _parsed(path)
    long_functions = [
        f"{node.name} ({(node.end_lineno or node.lineno) - node.lineno + 1} lines)"
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.end_lineno or node.lineno) - node.lineno + 1 > FUNCTION_LINE_CAP
    ]
    assert not long_functions, (
        f"{path.relative_to(repo_root())}: {', '.join(long_functions)} exceeds "
        f"{FUNCTION_LINE_CAP} lines"
    )


def test_every_cli_command_has_help_text():
    """`gigi --help` is where most people meet this project."""
    from gigi.cli import app

    undocumented = [
        command.callback.__name__
        for command in app.registered_commands
        if not (command.help or (command.callback.__doc__ or "").strip())
    ]
    assert not undocumented, f"CLI commands with no help text: {undocumented}"


# Two buckets, and the line between them is not a loophole.
#
# CAPABILITY is code that can compute something nothing else can: the models,
# the registry, the data layer, the adapters, the harness, the comparison and
# invariant logic. Growth here means the system learned a new concept, and that
# is what the budget is for.
#
# REPORTING re-presents what capability already computed -- the CLI, the static
# site, the review summary. It grows with what we choose to *show*, which is a
# different and much cheaper kind of growth.
REPORTING = ("cli", "site", "review.py", "typst.py")
CAPABILITY_BUDGET = 1800


def _is_reporting(path: pathlib.Path) -> bool:
    return path.name in REPORTING or any(part in REPORTING for part in path.parts)


def test_capability_stays_within_its_budget():
    """The number PLAN.md and CONTRIBUTING.md quote, kept honest."""
    capability = sum(code_lines(p) for p in MODULES if not _is_reporting(p))
    reporting = sum(code_lines(p) for p in MODULES if _is_reporting(p))
    assert capability <= CAPABILITY_BUDGET, (
        f"capability is {capability} code lines (reporting is {reporting}), over "
        f"the {CAPABILITY_BUDGET} budget. Raise it deliberately and say in "
        f"PLAN.md what bought it, or cut something."
    )
