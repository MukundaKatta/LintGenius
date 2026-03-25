"""Core analysis engine for LintGenius."""

from __future__ import annotations

import ast
import json
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from lintgenius.config import LintGeniusConfig
from lintgenius.utils import (
    classify_naming_issue,
    cyclomatic_complexity,
    find_hardcoded_secrets,
    function_line_count,
    get_class_nodes,
    get_docstring,
    get_function_nodes,
    get_import_nodes,
    is_pascal_case,
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Issue severity levels."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class Issue(BaseModel):
    """A single code quality issue found during analysis."""

    file: str = Field(description="File path where the issue was found.")
    line: int = Field(description="Line number of the issue.")
    severity: Severity = Field(description="Severity level.")
    code: str = Field(description="Short rule code, e.g. 'C001'.")
    message: str = Field(description="Human-readable description of the issue.")


class AnalysisReport(BaseModel):
    """Complete analysis report for a single file."""

    file: str
    issues: list[Issue] = Field(default_factory=list)
    quality_score: int = Field(default=100, ge=0, le=100)
    total_lines: int = 0
    num_functions: int = 0
    num_classes: int = 0

    def to_json(self) -> str:
        """Serialize the report to a JSON string."""
        return self.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# LintGenius — main analysis class
# ---------------------------------------------------------------------------


class LintGenius:
    """Static analysis engine that inspects Python source via the AST.

    Provides individual check methods that can be composed or run together
    through ``analyze_file``.
    """

    def __init__(self, config: Optional[LintGeniusConfig] = None) -> None:
        self.config = config or LintGeniusConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_file(self, filepath: str | Path) -> AnalysisReport:
        """Run all checks on a single Python file and return a report.

        Args:
            filepath: Path to the Python file to analyze.

        Returns:
            An ``AnalysisReport`` with all discovered issues and a quality score.
        """
        filepath = Path(filepath)
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        issues: list[Issue] = []
        file_str = str(filepath)

        # Run each checker
        issues.extend(self.check_complexity(source, tree, file_str))
        issues.extend(self.check_naming(source, tree, file_str))

        if self.config.check_docstrings:
            issues.extend(self.check_docstrings(source, tree, file_str))

        issues.extend(self.check_imports(source, tree, file_str))

        if self.config.check_security:
            issues.extend(self.check_security(source, tree, file_str))

        score = self.score_quality(issues)

        return AnalysisReport(
            file=file_str,
            issues=issues,
            quality_score=score,
            total_lines=len(source.splitlines()),
            num_functions=len(get_function_nodes(tree)),
            num_classes=len(get_class_nodes(tree)),
        )

    def analyze_source(self, source: str, filename: str = "<string>") -> AnalysisReport:
        """Analyze a source code string directly (useful for testing).

        Args:
            source: Python source code as a string.
            filename: Virtual filename for the report.

        Returns:
            An ``AnalysisReport``.
        """
        tree = ast.parse(source, filename=filename)
        issues: list[Issue] = []

        issues.extend(self.check_complexity(source, tree, filename))
        issues.extend(self.check_naming(source, tree, filename))

        if self.config.check_docstrings:
            issues.extend(self.check_docstrings(source, tree, filename))

        issues.extend(self.check_imports(source, tree, filename))

        if self.config.check_security:
            issues.extend(self.check_security(source, tree, filename))

        score = self.score_quality(issues)

        return AnalysisReport(
            file=filename,
            issues=issues,
            quality_score=score,
            total_lines=len(source.splitlines()),
            num_functions=len(get_function_nodes(tree)),
            num_classes=len(get_class_nodes(tree)),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_complexity(
        self, source: str, tree: ast.Module, filename: str
    ) -> list[Issue]:
        """Check cyclomatic complexity and function length.

        Returns issues for functions exceeding the configured thresholds.
        """
        issues: list[Issue] = []
        functions = get_function_nodes(tree)

        for func in functions:
            cc = cyclomatic_complexity(func)
            if cc > self.config.max_complexity:
                issues.append(
                    Issue(
                        file=filename,
                        line=func.lineno,
                        severity=Severity.ERROR,
                        code="C001",
                        message=(
                            f"Function '{func.name}' has cyclomatic complexity "
                            f"{cc} (max: {self.config.max_complexity})"
                        ),
                    )
                )

            length = function_line_count(func)
            if length > self.config.max_function_length:
                issues.append(
                    Issue(
                        file=filename,
                        line=func.lineno,
                        severity=Severity.WARN,
                        code="C002",
                        message=(
                            f"Function '{func.name}' is {length} lines long "
                            f"(max: {self.config.max_function_length})"
                        ),
                    )
                )

        return issues

    def check_naming(
        self, source: str, tree: ast.Module, filename: str
    ) -> list[Issue]:
        """Check naming conventions for functions and classes.

        Functions and methods should use snake_case; classes should use PascalCase.
        """
        issues: list[Issue] = []

        # Check function names
        for func in get_function_nodes(tree):
            issue_msg = classify_naming_issue(func.name, "snake_case")
            if issue_msg:
                issues.append(
                    Issue(
                        file=filename,
                        line=func.lineno,
                        severity=Severity.WARN,
                        code="N001",
                        message=f"Function {issue_msg}",
                    )
                )

        # Check class names
        for cls in get_class_nodes(tree):
            if not is_pascal_case(cls.name):
                issues.append(
                    Issue(
                        file=filename,
                        line=cls.lineno,
                        severity=Severity.WARN,
                        code="N002",
                        message=f"Class '{cls.name}' should be PascalCase",
                    )
                )

        return issues

    def check_docstrings(
        self, source: str, tree: ast.Module, filename: str
    ) -> list[Issue]:
        """Check for missing docstrings on public functions and classes."""
        issues: list[Issue] = []

        for func in get_function_nodes(tree):
            # Skip private/protected methods
            if func.name.startswith("_"):
                continue
            if get_docstring(func) is None:
                issues.append(
                    Issue(
                        file=filename,
                        line=func.lineno,
                        severity=Severity.WARN,
                        code="D001",
                        message=f"Missing docstring for function '{func.name}'",
                    )
                )

        for cls in get_class_nodes(tree):
            if cls.name.startswith("_"):
                continue
            if get_docstring(cls) is None:
                issues.append(
                    Issue(
                        file=filename,
                        line=cls.lineno,
                        severity=Severity.WARN,
                        code="D002",
                        message=f"Missing docstring for class '{cls.name}'",
                    )
                )

        return issues

    def check_imports(
        self, source: str, tree: ast.Module, filename: str
    ) -> list[Issue]:
        """Check for wildcard imports and duplicate import statements."""
        issues: list[Issue] = []
        seen_modules: dict[str, int] = {}

        for node in get_import_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                # Wildcard import check
                if node.names and any(alias.name == "*" for alias in node.names):
                    issues.append(
                        Issue(
                            file=filename,
                            line=node.lineno,
                            severity=Severity.INFO,
                            code="I001",
                            message=f"Wildcard import 'from {module_name} import *'",
                        )
                    )
                # Duplicate module import
                if module_name in seen_modules:
                    issues.append(
                        Issue(
                            file=filename,
                            line=node.lineno,
                            severity=Severity.INFO,
                            code="I002",
                            message=(
                                f"Duplicate import of '{module_name}' "
                                f"(first seen on line {seen_modules[module_name]})"
                            ),
                        )
                    )
                else:
                    seen_modules[module_name] = node.lineno

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in seen_modules:
                        issues.append(
                            Issue(
                                file=filename,
                                line=node.lineno,
                                severity=Severity.INFO,
                                code="I002",
                                message=(
                                    f"Duplicate import of '{alias.name}' "
                                    f"(first seen on line {seen_modules[alias.name]})"
                                ),
                            )
                        )
                    else:
                        seen_modules[alias.name] = node.lineno

        return issues

    def check_security(
        self, source: str, tree: ast.Module, filename: str
    ) -> list[Issue]:
        """Scan for security anti-patterns: eval/exec calls and hardcoded secrets."""
        issues: list[Issue] = []

        # Check for eval() and exec() calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_node = node.func
                if isinstance(func_node, ast.Name) and func_node.id in ("eval", "exec"):
                    issues.append(
                        Issue(
                            file=filename,
                            line=node.lineno,
                            severity=Severity.ERROR,
                            code="S001",
                            message=f"Use of '{func_node.id}()' is a security risk",
                        )
                    )

        # Check for hardcoded secrets
        for lineno, matched in find_hardcoded_secrets(source):
            issues.append(
                Issue(
                    file=filename,
                    line=lineno,
                    severity=Severity.ERROR,
                    code="S002",
                    message=f"Hardcoded secret detected: {matched}",
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------

    def generate_report(self, issues: list[Issue]) -> str:
        """Generate a plain-text summary report from a list of issues.

        Args:
            issues: List of Issue objects to summarize.

        Returns:
            A formatted multi-line string report.
        """
        if not issues:
            return "No issues found. Code looks great!"

        lines: list[str] = []
        lines.append(f"Found {len(issues)} issue(s):\n")

        for issue in sorted(issues, key=lambda i: (i.file, i.line)):
            icon = {"ERROR": "✗", "WARN": "⚠", "INFO": "ℹ"}.get(
                issue.severity.value, "?"
            )
            lines.append(
                f"  {icon}  [{issue.severity.value}] {issue.code}  "
                f"Line {issue.line}: {issue.message}"
            )

        return "\n".join(lines)

    def score_quality(self, issues: list[Issue]) -> int:
        """Compute a 0–100 quality score based on issue count and severity.

        Scoring:
        - Start at 100.
        - Deduct 10 points per ERROR.
        - Deduct 5 points per WARN.
        - Deduct 2 points per INFO.
        - Minimum score is 0.
        """
        score = 100
        for issue in issues:
            if issue.severity == Severity.ERROR:
                score -= 10
            elif issue.severity == Severity.WARN:
                score -= 5
            elif issue.severity == Severity.INFO:
                score -= 2

        return max(0, score)
