# LintGenius Architecture

## Overview

LintGenius is a Python-based code review assistant that uses the `ast` (Abstract Syntax Tree) module to perform static analysis on Python source files. It is designed as a modular, extensible CLI tool.

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Layer (Typer)                    │
│  Handles argument parsing, output formatting, and UX    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  LintGenius Core                        │
│  Orchestrates analysis passes over the AST              │
│                                                         │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Complexity   │ │ Naming       │ │ Docstring        │ │
│  │ Checker      │ │ Checker      │ │ Checker          │ │
│  └─────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Import       │ │ Security     │ │ Quality          │ │
│  │ Analyzer     │ │ Scanner      │ │ Scorer           │ │
│  └─────────────┘ └──────────────┘ └──────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Utilities Layer                        │
│  AST helpers, naming validators, complexity calculators  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Configuration                         │
│  Pydantic models for settings, TOML/env loading         │
└─────────────────────────────────────────────────────────┘
```

## Module Descriptions

### `cli.py`
The entry point for the application. Uses Typer to define CLI commands (`analyze`, `version`) and Rich for formatted terminal output. Handles file discovery, recursive directory scanning, and output format selection (Rich table or JSON).

### `core.py`
The central analysis engine. The `LintGenius` class exposes individual check methods:

| Method              | Purpose                                        |
|---------------------|------------------------------------------------|
| `analyze_file()`    | Parse a file and run all checks                |
| `check_complexity()`| Compute cyclomatic complexity per function     |
| `check_naming()`    | Validate PEP 8 naming conventions              |
| `check_docstrings()`| Ensure public callables have docstrings        |
| `check_imports()`   | Detect wildcard and duplicate imports           |
| `check_security()`  | Flag eval, exec, hardcoded secrets             |
| `generate_report()` | Compile issues into a structured report        |
| `score_quality()`   | Compute 0–100 quality score from issues        |

### `config.py`
Pydantic-based configuration with defaults. Loads from:
1. Built-in defaults
2. `.lintgenius.toml` project file
3. Environment variables (`LINTGENIUS_*`)

### `utils.py`
Pure utility functions with no side effects:
- AST node visitors and tree walkers
- Naming convention validation (snake_case, PascalCase)
- Cyclomatic complexity calculation from branching nodes
- Source line extraction helpers

## Data Flow

1. **Input**: User invokes `lintgenius analyze <path>`.
2. **Discovery**: CLI resolves files (single file or recursive glob).
3. **Parsing**: Each file is read and parsed into an AST via `ast.parse()`.
4. **Analysis**: The core engine runs each checker against the AST.
5. **Aggregation**: Issues are collected as `Issue` Pydantic models.
6. **Scoring**: A quality score is derived from issue counts and severities.
7. **Output**: Results are rendered via Rich tables or serialized as JSON.

## Extensibility

New checks can be added by:
1. Creating a method `check_<name>(code, tree)` on `LintGenius`.
2. Adding utility functions in `utils.py` if needed.
3. Registering the check in `analyze_file()`.

The architecture is intentionally simple — no plugin system or dynamic loading — to keep the codebase accessible to contributors.
