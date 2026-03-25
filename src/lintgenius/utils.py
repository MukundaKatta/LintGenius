"""Utility functions for AST analysis, naming checks, and complexity calculation."""

from __future__ import annotations

import ast
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Naming convention validators
# ---------------------------------------------------------------------------

_SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_UPPER_SNAKE_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_DUNDER_RE = re.compile(r"^__[a-z][a-z0-9_]*__$")


def is_snake_case(name: str) -> bool:
    """Return True if *name* follows snake_case convention."""
    return bool(_SNAKE_CASE_RE.match(name))


def is_pascal_case(name: str) -> bool:
    """Return True if *name* follows PascalCase convention."""
    return bool(_PASCAL_CASE_RE.match(name))


def is_upper_snake_case(name: str) -> bool:
    """Return True if *name* follows UPPER_SNAKE_CASE convention."""
    return bool(_UPPER_SNAKE_RE.match(name))


def is_dunder(name: str) -> bool:
    """Return True if *name* is a dunder (e.g. __init__)."""
    return bool(_DUNDER_RE.match(name))


def classify_naming_issue(name: str, expected: str) -> Optional[str]:
    """Return a human-readable issue string if *name* violates *expected* convention.

    Returns None if the name is compliant.
    """
    if expected == "snake_case":
        if is_dunder(name) or name.startswith("_"):
            return None
        if not is_snake_case(name):
            return f"'{name}' should be snake_case"
    elif expected == "PascalCase":
        if not is_pascal_case(name):
            return f"'{name}' should be PascalCase"
    return None


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def get_function_nodes(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return all top-level and nested function/method definitions."""
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)
    return functions


def get_class_nodes(tree: ast.Module) -> list[ast.ClassDef]:
    """Return all class definitions in the AST."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def get_import_nodes(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    """Return all import statements in the AST."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]


def function_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate the number of source lines a function spans."""
    if not node.body:
        return 0
    first_line = node.lineno
    last_line = max(_last_line(child) for child in ast.walk(node))
    return last_line - first_line + 1


def _last_line(node: ast.AST) -> int:
    """Return the last line number referenced by an AST node."""
    return getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)


def get_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from a function, class, or module node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            return node.body[0].value.value
    return None


# ---------------------------------------------------------------------------
# Complexity calculation
# ---------------------------------------------------------------------------

# AST node types that introduce a new branch (increase cyclomatic complexity).
_BRANCHING_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.BoolOp,
    ast.IfExp,      # ternary
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Compute the cyclomatic complexity of a function node.

    Starts at 1 (the function itself is one path) and increments for each
    branching construct found in the function body.
    """
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, _BRANCHING_NODES):
            if isinstance(child, ast.BoolOp):
                # Each additional boolean operator adds a branch
                complexity += len(child.values) - 1
            else:
                complexity += 1
    return complexity


# ---------------------------------------------------------------------------
# Security pattern helpers
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = re.compile(
    r"(password|secret|api_key|apikey|token|private_key)\s*=\s*['\"][^'\"]+['\"]",
    re.IGNORECASE,
)


def find_hardcoded_secrets(source: str) -> list[tuple[int, str]]:
    """Scan source code for hardcoded secret patterns.

    Returns a list of (line_number, matched_text) tuples.
    """
    results: list[tuple[int, str]] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = _SECRET_PATTERNS.search(line)
        if match:
            results.append((lineno, match.group(0).strip()))
    return results
