"""CLI entry point for LintGenius."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lintgenius import __version__
from lintgenius.config import LintGeniusConfig
from lintgenius.core import AnalysisReport, LintGenius, Severity

app = typer.Typer(
    name="lintgenius",
    help="AI-powered code review assistant for Python.",
    add_completion=False,
)
console = Console()


def _severity_style(severity: Severity) -> str:
    """Return a Rich style string for a severity level."""
    return {
        Severity.ERROR: "bold red",
        Severity.WARN: "yellow",
        Severity.INFO: "cyan",
    }[severity]


def _severity_icon(severity: Severity) -> str:
    """Return a display icon for a severity level."""
    return {
        Severity.ERROR: "✗",
        Severity.WARN: "⚠",
        Severity.INFO: "ℹ",
    }[severity]


def _render_report(report: AnalysisReport) -> None:
    """Render an analysis report as a Rich panel with table."""
    score_color = "green" if report.quality_score >= 80 else "yellow" if report.quality_score >= 50 else "red"

    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("", width=3)
    table.add_column("Sev", width=5)
    table.add_column("Line", width=6, justify="right")
    table.add_column("Code", width=6)
    table.add_column("Message")

    for issue in sorted(report.issues, key=lambda i: i.line):
        style = _severity_style(issue.severity)
        table.add_row(
            _severity_icon(issue.severity),
            issue.severity.value,
            str(issue.line),
            issue.code,
            issue.message,
            style=style,
        )

    header = (
        f"[bold]File:[/bold] {report.file}\n"
        f"[bold]Quality Score:[/bold] [{score_color}]{report.quality_score}/100[/{score_color}]  |  "
        f"Lines: {report.total_lines}  |  "
        f"Functions: {report.num_functions}  |  "
        f"Classes: {report.num_classes}"
    )

    if report.issues:
        console.print(Panel(header, title="LintGenius Report", border_style="blue"))
        console.print(table)
    else:
        console.print(
            Panel(
                f"{header}\n\n[green]No issues found. Code looks great![/green]",
                title="LintGenius Report",
                border_style="green",
            )
        )


@app.command()
def analyze(
    path: Path = typer.Argument(..., help="File or directory to analyze."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursively scan directories."),
    format: str = typer.Option("rich", "--format", "-f", help="Output format: rich or json."),
) -> None:
    """Analyze Python file(s) for code quality issues."""
    config = LintGeniusConfig.load()
    engine = LintGenius(config)

    files: list[Path] = []
    if path.is_file():
        files.append(path)
    elif path.is_dir():
        pattern = "**/*.py" if recursive else "*.py"
        files.extend(sorted(path.glob(pattern)))
    else:
        console.print(f"[red]Error:[/red] Path '{path}' does not exist.")
        raise typer.Exit(code=1)

    if not files:
        console.print(f"[yellow]No Python files found in '{path}'.[/yellow]")
        raise typer.Exit(code=0)

    reports: list[AnalysisReport] = []
    for filepath in files:
        try:
            report = engine.analyze_file(filepath)
            reports.append(report)
        except SyntaxError as exc:
            console.print(f"[red]Syntax error in {filepath}:[/red] {exc}")
        except Exception as exc:
            console.print(f"[red]Error analyzing {filepath}:[/red] {exc}")

    if format == "json":
        output = [json.loads(r.to_json()) for r in reports]
        console.print_json(json.dumps(output, indent=2))
    else:
        for report in reports:
            _render_report(report)
            console.print()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
) -> None:
    """LintGenius — AI-powered code review assistant."""
    if version:
        console.print(f"LintGenius v{__version__}")
        raise typer.Exit()
