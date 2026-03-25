# Contributing to LintGenius

Thank you for your interest in contributing to LintGenius! This guide will help you get started.

## Development Setup

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/your-username/LintGenius.git
   cd LintGenius
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. **Install dev dependencies**:

   ```bash
   make dev
   ```

## Development Workflow

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feat/your-feature
   ```

2. Make your changes and write tests.

3. Run the test suite:

   ```bash
   make test
   ```

4. Run linters and formatters:

   ```bash
   make lint
   make format
   ```

5. Commit with a descriptive message:

   ```bash
   git commit -m "feat: add new check for unused variables"
   ```

6. Push and open a Pull Request.

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — A new feature
- `fix:` — A bug fix
- `docs:` — Documentation changes
- `test:` — Adding or updating tests
- `refactor:` — Code refactoring (no feature or fix)
- `chore:` — Maintenance tasks

## Adding a New Check

To add a new code analysis check:

1. Add the check method to `src/lintgenius/core.py` in the `LintGenius` class.
2. Add any helper functions to `src/lintgenius/utils.py`.
3. Register the check in the `analyze_file` method.
4. Write tests in `tests/test_core.py`.
5. Update documentation if needed.

## Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions under 50 lines where possible
- Maximum line length: 100 characters

## Reporting Issues

When reporting a bug, please include:

- Python version
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Any relevant error output

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
