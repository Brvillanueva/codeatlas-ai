"""Central configuration for repository analysis."""

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".github",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "env",
        "htmlcov",
        "node_modules",
        "venv",
    }
)


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Configuration passed through the deterministic analysis pipeline."""

    repository_path: Path
    excluded_directories: frozenset[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDED_DIRECTORIES
    )
    ignored_files: frozenset[str] = field(default_factory=lambda: frozenset({".env"}))
    respect_codeatlasignore: bool = True
