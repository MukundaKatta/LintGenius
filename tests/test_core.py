"""Tests for LintGenius core analysis engine."""

from __future__ import annotations

import textwrap

import pytest

from lintgenius.config import LintGeniusConfig
from lintgenius.core import LintGenius, Severity


@pytest.fixture
def engine() -> LintGenius:
    """Create a LintGenius engine with default config."""
    return LintGenius(LintGeniusConfig())


class TestCheckComplexity:
    """Tests for cyclomatic complexity and function length checks."""

    def test_simple_function_passes(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def greet(name):
                \"\"\"Say hello.\"\"\"
                return f"Hello, {name}"
        """)
        report = engine.analyze_source(source)
        complexity_issues = [i for i in report.issues if i.code.startswith("C")]
        assert len(complexity_issues) == 0

    def test_high_complexity_flagged(self, engine: LintGenius) -> None:
        # Build a function with many branches to exceed complexity threshold
        source = textwrap.dedent("""\
            def complex_func(x):
                \"\"\"A very branchy function.\"\"\"
                if x > 0:
                    pass
                if x > 1:
                    pass
                if x > 2:
                    pass
                if x > 3:
                    pass
                if x > 4:
                    pass
                if x > 5:
                    pass
                if x > 6:
                    pass
                if x > 7:
                    pass
                if x > 8:
                    pass
                if x > 9:
                    pass
                if x > 10:
                    pass
                return x
        """)
        report = engine.analyze_source(source)
        complexity_issues = [i for i in report.issues if i.code == "C001"]
        assert len(complexity_issues) == 1
        assert complexity_issues[0].severity == Severity.ERROR


class TestCheckNaming:
    """Tests for naming convention checks."""

    def test_camel_case_function_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def processData(data):
                \"\"\"Process the data.\"\"\"
                return data
        """)
        report = engine.analyze_source(source)
        naming_issues = [i for i in report.issues if i.code == "N001"]
        assert len(naming_issues) == 1
        assert "snake_case" in naming_issues[0].message

    def test_snake_case_function_passes(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def process_data(data):
                \"\"\"Process the data.\"\"\"
                return data
        """)
        report = engine.analyze_source(source)
        naming_issues = [i for i in report.issues if i.code == "N001"]
        assert len(naming_issues) == 0

    def test_non_pascal_class_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            class my_class:
                \"\"\"A poorly named class.\"\"\"
                pass
        """)
        report = engine.analyze_source(source)
        naming_issues = [i for i in report.issues if i.code == "N002"]
        assert len(naming_issues) == 1


class TestCheckDocstrings:
    """Tests for docstring checks."""

    def test_missing_docstring_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def no_docs():
                return 42
        """)
        report = engine.analyze_source(source)
        doc_issues = [i for i in report.issues if i.code == "D001"]
        assert len(doc_issues) == 1

    def test_present_docstring_passes(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def documented():
                \"\"\"This function is documented.\"\"\"
                return 42
        """)
        report = engine.analyze_source(source)
        doc_issues = [i for i in report.issues if i.code == "D001"]
        assert len(doc_issues) == 0


class TestCheckSecurity:
    """Tests for security checks."""

    def test_eval_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def run(code):
                \"\"\"Run arbitrary code.\"\"\"
                return eval(code)
        """)
        report = engine.analyze_source(source)
        security_issues = [i for i in report.issues if i.code == "S001"]
        assert len(security_issues) == 1
        assert security_issues[0].severity == Severity.ERROR

    def test_hardcoded_password_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def connect():
                \"\"\"Connect to the database.\"\"\"
                password = "supersecret123"
                return password
        """)
        report = engine.analyze_source(source)
        secret_issues = [i for i in report.issues if i.code == "S002"]
        assert len(secret_issues) == 1


class TestCheckImports:
    """Tests for import checks."""

    def test_wildcard_import_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            from os import *

            def run():
                \"\"\"Do something.\"\"\"
                pass
        """)
        report = engine.analyze_source(source)
        import_issues = [i for i in report.issues if i.code == "I001"]
        assert len(import_issues) == 1

    def test_duplicate_import_flagged(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            from os import path
            from os import getcwd

            def run():
                \"\"\"Do something.\"\"\"
                pass
        """)
        report = engine.analyze_source(source)
        dup_issues = [i for i in report.issues if i.code == "I002"]
        assert len(dup_issues) == 1


class TestQualityScore:
    """Tests for the quality scoring system."""

    def test_perfect_score(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            def greet(name):
                \"\"\"Say hello.\"\"\"
                return f"Hello, {name}"
        """)
        report = engine.analyze_source(source)
        assert report.quality_score == 100

    def test_score_decreases_with_issues(self, engine: LintGenius) -> None:
        source = textwrap.dedent("""\
            from os import *

            def processData(x):
                return eval(x)
        """)
        report = engine.analyze_source(source)
        assert report.quality_score < 100
        assert report.quality_score >= 0
