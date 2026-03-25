"""Configuration management for LintGenius."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class LintGeniusConfig(BaseModel):
    """Configuration settings for LintGenius analysis."""

    max_complexity: int = Field(
        default=10,
        ge=1,
        description="Maximum allowed cyclomatic complexity per function.",
    )
    max_function_length: int = Field(
        default=50,
        ge=1,
        description="Maximum allowed function length in lines.",
    )
    naming_convention: str = Field(
        default="snake_case",
        description="Expected naming convention for functions and variables.",
    )
    check_docstrings: bool = Field(
        default=True,
        description="Whether to check for missing docstrings.",
    )
    check_security: bool = Field(
        default=True,
        description="Whether to run security-related checks.",
    )
    ignore_patterns: list[str] = Field(
        default_factory=list,
        description="File name patterns to ignore during analysis.",
    )
    output_format: str = Field(
        default="rich",
        description="Output format: 'rich' for terminal or 'json'.",
    )

    @classmethod
    def load(cls, project_dir: Optional[Path] = None) -> "LintGeniusConfig":
        """Load configuration from TOML file and environment variables.

        Priority: environment variables > TOML file > defaults.
        """
        config_data: dict = {}

        # Attempt to load from .lintgenius.toml
        if project_dir is None:
            project_dir = Path.cwd()

        toml_path = project_dir / ".lintgenius.toml"
        if toml_path.exists():
            config_data = _load_toml(toml_path)

        # Override with environment variables
        env_map = {
            "LINTGENIUS_MAX_COMPLEXITY": "max_complexity",
            "LINTGENIUS_MAX_FUNCTION_LENGTH": "max_function_length",
            "LINTGENIUS_NAMING_CONVENTION": "naming_convention",
            "LINTGENIUS_CHECK_DOCSTRINGS": "check_docstrings",
            "LINTGENIUS_CHECK_SECURITY": "check_security",
            "LINTGENIUS_OUTPUT_FORMAT": "output_format",
        }

        for env_key, field_name in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                # Convert string booleans
                if value.lower() in ("true", "1", "yes"):
                    config_data[field_name] = True
                elif value.lower() in ("false", "0", "no"):
                    config_data[field_name] = False
                else:
                    # Try integer conversion
                    try:
                        config_data[field_name] = int(value)
                    except ValueError:
                        config_data[field_name] = value

        return cls(**config_data)


def _load_toml(path: Path) -> dict:
    """Parse a TOML config file and return the [lintgenius] section."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with open(path, "rb") as f:
        data = tomllib.load(f)

    return data.get("lintgenius", {})
